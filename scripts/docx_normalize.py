#!/usr/bin/env python3
"""Normalize a pandoc-generated .docx so that it validates against the ECMA-376/ISO 29500 transitional schemas.

pandoc 3.1 writes a few elements in an order the schemas do not allow (style, paragraph, table and cell properties,
settings, OMML delimiter and run properties), short numbering ids, a stray '>' in one style, and declares images
only through per-part overrides. Word tolerates all of this; strict validators do not. This script only reorders
children, pads ids, removes the stray character and adds a Default content type. Text and formatting are unchanged.

Usage: python scripts/docx_normalize.py file.docx   (rewrites the file in place)
"""
import re
import sys
import zipfile

from lxml import etree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"

ORDER = {
    (W, "style"): "name aliases basedOn next link autoRedefine hidden uiPriority semiHidden unhideWhenUsed qFormat locked "
                  "personal personalCompose personalReply rsid pPr rPr tblPr trPr tcPr tblStylePr",
    (W, "pPr"): "pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs "
                "suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd "
                "snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment "
                "textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange",
    (W, "tblPr"): "tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing tblInd "
                  "tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription tblPrChange",
    (W, "tcPr"): "cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign hideMark "
                 "headers cellIns cellDel cellMerge tcPrChange",
    (W, "settings"): "writeProtection view zoom removePersonalInformation removeDateAndTime doNotDisplayPageBoundaries "
                     "displayBackgroundShape printPostScriptOverText printFractionalCharacterWidth printFormsData "
                     "embedTrueTypeFonts embedSystemFonts saveSubsetFonts saveFormsData mirrorMargins alignBordersAndEdges "
                     "bordersDoNotSurroundHeader bordersDoNotSurroundFooter gutterAtTop hideSpellingErrors "
                     "hideGrammaticalErrors activeWritingStyle proofState formsDesign attachedTemplate linkStyles "
                     "stylePaneFormatFilter stylePaneSortMethod documentType mailMerge revisionView trackRevisions "
                     "doNotTrackMoves doNotTrackFormatting documentProtection autoFormatOverride styleLockTheme "
                     "styleLockQFSet defaultTabStop autoHyphenation consecutiveHyphenLimit hyphenationZone "
                     "doNotHyphenateCaps showEnvelope summaryLength clickAndTypeStyle defaultTableStyle evenAndOddHeaders "
                     "bookFoldRevPrinting bookFoldPrinting bookFoldPrintingSheets drawingGridHorizontalSpacing "
                     "drawingGridVerticalSpacing displayHorizontalDrawingGridEvery displayVerticalDrawingGridEvery "
                     "doNotUseMarginsForDrawingGridOrigin drawingGridHorizontalOrigin drawingGridVerticalOrigin "
                     "doNotShadeFormData noPunctuationKerning characterSpacingControl printTwoOnOne "
                     "strictFirstAndLastChars noLineBreaksAfter noLineBreaksBefore savePreviewPicture "
                     "doNotValidateAgainstSchema saveInvalidXml ignoreMixedContent alwaysShowPlaceholderText "
                     "doNotDemarcateInvalidXml saveXmlDataOnly useXSLTWhenSaving saveThroughXslt showXMLTags "
                     "alwaysMergeEmptyNamespace updateFields hdrShapeDefaults footnotePr endnotePr compat docVars rsids "
                     "mathPr attachedSchema themeFontLang clrSchemeMapping doNotIncludeSubdocsInStats "
                     "doNotAutoCompressPictures forceUpgrade captions readModeInkLockDown smartTagType schemaLibrary "
                     "shapeDefaults doNotEmbedSmartTags decimalSymbol listSeparator",
    (M, "dPr"): "begChr sepChr endChr grow shp ctrlPr",
    (M, "rPr"): "lit nor scr sty brk aln",
}
ORDER = {k: {n: i for i, n in enumerate(v.split())} for k, v in ORDER.items()}


def _local(e):
    q = ET.QName(e)
    return q.namespace, q.localname


def _fix_tree(root):
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        ns, name = _local(el)
        key = (ns, name)
        if key == (M, "rPr"):
            kids = {_local(c)[1] for c in el if isinstance(c.tag, str)}
            if "nor" in kids and kids & {"scr", "sty"}:       # nor excludes scr/sty in CT_RPR
                for c in list(el):
                    if isinstance(c.tag, str) and _local(c)[1] == "nor":
                        el.remove(c)
        if key in ORDER:
            rank = ORDER[key]
            kids = [c for c in el if isinstance(c.tag, str)]
            if any(_local(c)[1] not in rank for c in kids):
                continue                                      # unknown child: leave untouched
            for c in kids:
                c.tail = None
            for c in kids:
                el.remove(c)
            for c in sorted(kids, key=lambda c: rank[_local(c)[1]]):
                el.append(c)
            if el.text is not None and not el.text.strip():
                el.text = None
    # character content inside element-only containers (pandoc writes a stray '>' after one colour)
    for el in list(root.iter("{%s}rPr" % W, "{%s}pPr" % W, "{%s}style" % W)):
        for c in el:
            if c.tail and c.tail.strip():
                c.tail = None
    return root


def normalize(path):
    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    out = []
    for info, data in items:
        n = info.filename
        if n in ("word/document.xml", "word/styles.xml", "word/settings.xml"):
            root = ET.fromstring(data)
            data = ET.tostring(_fix_tree(root), xml_declaration=True, encoding="UTF-8", standalone=True)
        elif n == "word/numbering.xml":
            data = re.sub(rb'(<w:nsid w:val=")([0-9A-Fa-f]{1,7})(")', lambda m: m.group(1) + m.group(2).rjust(8, b"0") + m.group(3), data)
        elif n == "[Content_Types].xml":
            s = data.decode("utf-8")
            for ext, ct in (("png", "image/png"), ("jpeg", "image/jpeg"), ("jpg", "image/jpeg")):
                if f'Extension="{ext}"' not in s and any(i.filename.lower().endswith("." + ext) for i, _ in items):
                    s = s.replace("<Default ", f'<Default Extension="{ext}" ContentType="{ct}" /><Default ', 1)
            data = s.encode("utf-8")
        out.append((info, data))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in out:
            z.writestr(info, data)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        normalize(p)
        print("normalized", p)
