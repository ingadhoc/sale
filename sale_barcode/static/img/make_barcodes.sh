#!/bin/sh

barcode -t 2x7+40+40 -m 50x30 -p "210x297mm" -e code128b  << BARCODES | ps2pdf - - > barcodes_actions.pdf
OCDSAVE
OCDDISC
OCDEDIT
OBTvalidate
OBTcancel
OBTprint-op
OCDPREV
OCDNEXT
OCDPAGERFIRST
OCDPAGERLAST
BARCODES
