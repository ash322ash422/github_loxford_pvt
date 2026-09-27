import copy

def _copy_worksheet(src_ws, dst_ws) -> None:
    """Copy cell values + styles, merged ranges, column widths, row heights, and
    freeze panes from src_ws into dst_ws. Plain pandas read_excel/to_excel would
    silently drop all of this (merged-cell content collapses to NaN and every
    fill/font/wrap-text/column-width setting is lost), which matters here since
    the source sheets are built with real formatting, not just raw data."""
    for row in src_ws.iter_rows():
        for cell in row:
            new_cell = dst_ws.cell(row=cell.row, column=cell.column, value=cell.value)
            if cell.has_style:
                new_cell.font = copy.copy(cell.font)
                new_cell.border = copy.copy(cell.border)
                new_cell.fill = copy.copy(cell.fill)
                new_cell.alignment = copy.copy(cell.alignment)
                new_cell.protection = copy.copy(cell.protection)
                new_cell.number_format = cell.number_format

    for merged_range in src_ws.merged_cells.ranges:
        dst_ws.merge_cells(str(merged_range))

    for col_letter, dim in src_ws.column_dimensions.items():
        if dim.width is not None:
            dst_ws.column_dimensions[col_letter].width = dim.width

    for row_idx, dim in src_ws.row_dimensions.items():
        if dim.height is not None:
            dst_ws.row_dimensions[row_idx].height = dim.height

    if src_ws.freeze_panes:
        dst_ws.freeze_panes = src_ws.freeze_panes


