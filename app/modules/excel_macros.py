from flask import Blueprint, render_template, jsonify

bp = Blueprint('excel_macros', __name__)

# VBA Macros
MACROS = {
    'cleanup': {
        'name': 'Clean Up & Format',
        'description': 'Formats credit card batch Excel for copy-paste readiness',
        'code': '''Sub ProcessDataAndFormat()
    Dim wsOriginal As Worksheet, wsNew As Worksheet
    Dim lastRow As Long, i As Long
    Dim fName As String, lName As String
    
    Set wsOriginal = ActiveSheet
    wsOriginal.Copy After:=wsOriginal
    Set wsNew = wsOriginal.Next
    wsNew.Name = "Formatted"
    
    ' Find last row
    lastRow = wsNew.Cells(wsNew.Rows.Count, "E").End(xlUp).Row
    
    ' Sort by card type then invoice number
    With wsNew.Sort
        .SortFields.Clear
        .SortFields.Add2 Key:=Range("F2:F" & lastRow), Order:=xlAscending
        .SortFields.Add2 Key:=Range("B2:B" & lastRow), Order:=xlAscending
        .SetRange Range("A1:J" & lastRow)
        .Header = xlYes
        .Apply
    End With
    
    ' Process each row
    For i = 1 To lastRow
        ' Format names: lastname, firstname -> firstname lastname
        If InStr(wsNew.Cells(i, 5).Value, ",") > 0 Then
            lName = Trim(Left(wsNew.Cells(i, 5).Value, InStr(wsNew.Cells(i, 5).Value, ",") - 1))
            fName = Trim(Mid(wsNew.Cells(i, 5).Value, InStr(wsNew.Cells(i, 5).Value, ",") + 1))
            wsNew.Cells(i, 5).Value = fName & " " & lName
        End If
        
        ' Format card types
        Select Case wsNew.Cells(i, 6).Value
            Case "A": wsNew.Cells(i, 6).Value = "AMEX-"
            Case "V": wsNew.Cells(i, 6).Value = "VISA-"
            Case "M": wsNew.Cells(i, 6).Value = "MC-"
        End Select
        
        ' Combine card type with last 4 digits
        wsNew.Cells(i, 6).Value = wsNew.Cells(i, 6).Value & Right(wsNew.Cells(i, 7).Value, 4)
    Next i
    
    ' Clean up columns
    wsNew.Columns("G").ClearContents
    wsNew.Columns("A:A,C:D,H:I").Delete
    
    ' Move column B to last position
    wsNew.Columns("B").Cut
    wsNew.Columns("F").Insert Shift:=xlToRight
    
    ' Format appearance
    With wsNew.Range("A1").Resize(lastRow, 5)
        .Interior.Color = RGB(0, 0, 0)
        .Font.Color = RGB(255, 255, 255)
        .Style = "Output"
    End With
    
    ' Auto-fit columns
    wsNew.Columns("A:E").AutoFit
    wsNew.Rows.RowHeight = 15
    
    ' Highlight MC rows
    For i = 1 To lastRow
        If Left(wsNew.Cells(i, 2).Value, 2) = "MC" Then
            wsNew.Rows(i).Columns("A:E").Interior.Color = RGB(35, 35, 35)
        End If
    Next i
    
    MsgBox "Processing complete!", vbInformation
End Sub'''
    },
    'sort_sum': {
        'name': 'Sort and Sum',
        'description': 'Calculates totals for each payment category',
        'code': '''Sub SortAndSum()
    Dim ws As Worksheet
    Dim lastRow As Long, i As Long
    Dim sumAmexPROJ As Double, sumMVDPROJ As Double
    Dim sumAmexRep As Double, sumMVDRep As Double
    Dim totalSum As Double
    
    Set ws = ActiveSheet
    lastRow = ws.Cells(ws.Rows.Count, "F").End(xlUp).Row
    
    ' Initialize sums
    sumAmexPROJ = 0: sumMVDPROJ = 0
    sumAmexRep = 0: sumMVDRep = 0
    totalSum = 0
    
    ' Calculate sums
    For i = 2 To lastRow
        totalSum = totalSum + ws.Cells(i, "J").Value
        
        ' Check card type and invoice type
        If ws.Cells(i, "F").Value Like "*A*" Then
            If ws.Cells(i, "B").Value Like "*P*" Then
                sumAmexPROJ = sumAmexPROJ + ws.Cells(i, "J").Value
            ElseIf ws.Cells(i, "B").Value Like "*R*" And Not ws.Cells(i, "B").Value Like "*P*" Then
                sumAmexRep = sumAmexRep + ws.Cells(i, "J").Value
            End If
        ElseIf ws.Cells(i, "F").Value Like "*[MVD]*" Then
            If ws.Cells(i, "B").Value Like "*P*" Then
                sumMVDPROJ = sumMVDPROJ + ws.Cells(i, "J").Value
            ElseIf ws.Cells(i, "B").Value Like "*R*" And Not ws.Cells(i, "B").Value Like "*P*" Then
                sumMVDRep = sumMVDRep + ws.Cells(i, "J").Value
            End If
        End If
    Next i
    
    ' Output results
    ws.Cells(1, "L").Value = "Amex PROJ"
    ws.Cells(2, "L").Value = sumAmexPROJ
    ws.Cells(1, "M").Value = "M/V/D PROJ"
    ws.Cells(2, "M").Value = sumMVDPROJ
    ws.Cells(1, "N").Value = "Amex Rep"
    ws.Cells(2, "N").Value = sumAmexRep
    ws.Cells(1, "O").Value = "M/V/D Rep"
    ws.Cells(2, "O").Value = sumMVDRep
    ws.Cells(1, "P").Value = "Total"
    ws.Cells(2, "P").Value = totalSum
    
    ' Format output
    ws.Range("L1:P2").Font.Bold = True
    ws.Columns("L:P").AutoFit
    
    MsgBox "Calculation complete!", vbInformation
End Sub'''
    }
}

@bp.route('/')
def index():
    """Excel macros page."""
    return render_template('excel_macros.html', macros=MACROS)

@bp.route('/macro/<macro_id>')
def get_macro(macro_id):
    """Get specific macro code."""
    if macro_id in MACROS:
        return jsonify({
            'status': 'success',
            'macro': MACROS[macro_id]
        })
    return jsonify({'status': 'error', 'message': 'Macro not found'}), 404