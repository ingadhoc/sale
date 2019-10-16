#!/bin/sh

barcode -t 2x7+40+40 -m 50x30 -p "210x297mm" -e code128b  << BARCODES | ps2pdf - - > barcodes_actions.pdf
O-CMD.SAVE
O-CMD.DISCARD
O-CMD.EDIT
O-BTN.validate
O-BTN.cancel
O-BTN.print-op
O-CMD.PREV
O-CMD.NEXT
O-CMD.PAGER-FIRST
O-CMD.PAGER-LAST
BARCODES
