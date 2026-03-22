"""
MarkdownDocument - Parser für Markdown-Dokumente mit Baumstruktur.
"""

from enum import IntEnum
from typing import Any, Dict, List, Optional, Protocol, TypedDict, cast


# Basic Framework Imports
from ..container_utils.knot_object import KnotObject
from ..container_utils.container_in_memory import ContainerInMemory
from ..proc_frame import log_msg
from ..ext_filesystem import file_must_exist


# Explizites Typing für optionale chardet-Dependency
class ChardetResult(TypedDict):
    """Typisiertes Ergebnis von chardet.detect()."""
    encoding: Optional[str]
    confidence: float


class ChardetProtocol(Protocol):
    """Protocol für chardet-Modul Interface."""
    def detect(self, byte_str: bytes) -> ChardetResult: ...


# Optional: chardet für bessere Encoding-Erkennung
_chardet: Optional[ChardetProtocol] = None
try:
    import chardet
    _chardet = chardet
except ImportError:
    log_msg("chardet nicht installiert - verwende nur BOM-Detection")


class MarkdownLineType(IntEnum):
    """Enum für verschiedene Markdown-Zeilentypen."""
    Heading1 = 1
    Heading2 = 2
    Heading3 = 3
    Heading4 = 4
    Heading5 = 5
    Heading6 = 6
    Paragraph = 7
    ListItemOrdered = 8
    ListItemUnordered = 9
    CodeBlockStart = 10
    CodeBlockEnd = 11
    CodeBlockContent = 12
    TableRow = 13
    TableDelimiter = 14
    Blockquote = 15
    HorizontalRule = 16
    FrontMatterDelimiter = 17
    EmptyLine = 18


class MarkdownParserState(IntEnum):
    """Enum für Parser-Zustände."""
    Normal = 1
    InCodeBlock = 2
    InTable = 3
    InFrontMatter = 4
    InBlockquote = 5
    InList = 6


class MarkdownDocument:
    """
    Parser und Prozessor für Markdown-Dokumente.
    Erstellt eine hierarchische Baumstruktur aus KnotObject-Knoten.

    """

    def __init__(self):
        """Konstruktor."""
        # Private Eigenschaften
        self.m_CurrentNode: Optional[KnotObject] = None
        self.m_RootNode: Optional[KnotObject] = KnotObject()
        self.m_RootNode.init("", "", None)
        self.m_CurrentNode = self.m_RootNode

        self.m_SourceFile: str = ""
        self.m_NodeIndex: Dict[str, KnotObject] = {}
        self.m_HeadingStack: List[KnotObject] = []
        self.m_LineCounter: int = 0
        self.m_Metadata: Dict[str, Any] = {}
        self.m_ParserState: MarkdownParserState = MarkdownParserState.Normal
        self.m_CurrentTableData: List[List[str]] = []
        self.m_FileEncoding: str = "UTF-8"
        self.m_CodeBlockLanguage: str = ""
        self.m_TableHeaders: List[str] = []

    def _get_root_node(self) -> KnotObject:
        """Gibt den Root-Knoten zurück oder wirft Fehler wenn clean_up() aufgerufen wurde."""
        if self.m_RootNode is None:
            from ..proc_frame import log_and_raise
            log_and_raise(RuntimeError("MarkdownDocument wurde bereits mit clean_up() freigegeben"))
        return self.m_RootNode

    def load_from_file(self, sFilePath: str) -> None:
        """Lädt und parst eine Markdown-Datei."""
        # Pfad validieren
        file_must_exist(sFilePath)
        self.m_SourceFile = sFilePath

        # Encoding erkennen
        self.m_FileEncoding = self.detect_encoding(sFilePath)

        # Datei mit korrektem Encoding einlesen
        sContent = self.read_file_with_encoding(sFilePath, self.m_FileEncoding)

        # Inhalt parsen
        self.load_from_string(sContent)

        log_msg(f"Markdown-Datei '{sFilePath}' erfolgreich geladen. Encoding: {self.m_FileEncoding}")

    def load_from_string(self, sContent: str) -> None:
        """Parst einen Markdown-String direkt."""
        # Sicherstellen dass Klasse initialisiert ist
        if self.m_RootNode is None:
            self.m_RootNode = KnotObject()
            self.m_RootNode.init("", "", None)
            self.m_CurrentNode = self.m_RootNode

        # Zeilenumbrüche normalisieren
        sContent = sContent.replace('\r\n', '\n')
        sContent = sContent.replace('\r', '\n')

        # In Zeilen aufteilen
        aLines = sContent.split('\n')

        # Jede Zeile parsen
        for i in range(len(aLines)):
            self.m_LineCounter = i + 1
            self.parse_line(aLines[i])

        # Offene Strukturen abschließen
        self.finalize_open_structures()

        log_msg(f"Markdown-String erfolgreich geparst. {self.m_LineCounter} Zeilen verarbeitet.")

    def detect_encoding(self, sFilePath: str) -> str:
        """Erkennt die Dateikodierung."""
        # BOM-Detection
        with open(sFilePath, 'rb') as oStream:
            byteArray = oStream.read(3)

            encoding = "UTF-8"  # Default

            if len(byteArray) >= 3:
                # UTF-8 BOM: EF BB BF
                if byteArray[0] == 0xEF and byteArray[1] == 0xBB and byteArray[2] == 0xBF:
                    encoding = "UTF-8"
                # UTF-16 LE BOM: FF FE
                elif len(byteArray) >= 2 and byteArray[0] == 0xFF and byteArray[1] == 0xFE:
                    encoding = "UTF-16"
                # UTF-16 BE BOM: FE FF
                elif len(byteArray) >= 2 and byteArray[0] == 0xFE and byteArray[1] == 0xFF:
                    encoding = "UTF-16"
                else:
                    # Kein BOM gefunden - chardet als Fallback
                    if _chardet is not None:
                        oStream.seek(0)
                        sample = oStream.read(10000)
                        if sample:
                            result = _chardet.detect(sample)
                            if result['confidence'] > 0.7:
                                encoding = result['encoding'] or "UTF-8"

        return encoding

    def read_file_with_encoding(self, sFilePath: str, sEncoding: str) -> str:
        """Liest Datei mit korrektem Encoding."""
        # Python-Encoding-Namen anpassen
        encoding_map = {
            "UTF-8": "utf-8-sig",  # BOM automatisch entfernen
            "UTF-16": "utf-16",
        }
        python_encoding = encoding_map.get(sEncoding, sEncoding.lower())

        try:
            with open(sFilePath, 'r', encoding=python_encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback
            with open(sFilePath, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()

    def parse_line(self, sLine: str) -> None:
        """Verarbeitet eine einzelne Zeile."""
        # Zeilentyp identifizieren
        lineType = self.identify_line_type(sLine)

        # Je nach Parser-Status und Zeilentyp verarbeiten
        if self.m_ParserState == MarkdownParserState.Normal:
            self.process_normal_line(sLine, lineType)
        elif self.m_ParserState == MarkdownParserState.InCodeBlock:
            self.process_code_block_line(sLine, lineType)
        elif self.m_ParserState == MarkdownParserState.InTable:
            self.process_table_line(sLine, lineType)
        elif self.m_ParserState == MarkdownParserState.InFrontMatter:
            self.process_front_matter_line(sLine, lineType)
        elif self.m_ParserState == MarkdownParserState.InBlockquote:
            self.process_blockquote_line(sLine, lineType)
        elif self.m_ParserState == MarkdownParserState.InList:
            self.process_list_line(sLine, lineType)

    def identify_line_type(self, sLine: str) -> MarkdownLineType:
        """Bestimmt den Typ einer Zeile."""
        # Leere Zeile
        if sLine.strip() == "":
            return MarkdownLineType.EmptyLine

        # Frontmatter-Delimiter (---)
        if sLine == "---":
            return MarkdownLineType.FrontMatterDelimiter

        # Horizontale Linie
        if sLine in ["***", "---", "___"]:
            return MarkdownLineType.HorizontalRule

        # Code-Block Start/Ende (```)
        if sLine[:3] == "```":
            if self.m_ParserState == MarkdownParserState.InCodeBlock:
                return MarkdownLineType.CodeBlockEnd
            else:
                return MarkdownLineType.CodeBlockStart

        # In Code-Block
        if self.m_ParserState == MarkdownParserState.InCodeBlock:
            return MarkdownLineType.CodeBlockContent

        # Überschriften
        if len(sLine) > 0 and sLine[0] == "#":
            headingLevel = self.get_heading_level(sLine)
            if headingLevel > 0 and headingLevel <= 6:
                return MarkdownLineType(headingLevel)  # Heading1 bis Heading6

        # Tabellen-Delimiter (|---|---|)
        if self.is_table_delimiter(sLine):
            return MarkdownLineType.TableDelimiter

        # Tabellen-Zeile
        if "|" in sLine and (self.m_ParserState == MarkdownParserState.InTable or self.could_be_table_start(sLine)):
            return MarkdownLineType.TableRow

        # Ungeordnete Liste
        trimmed = sLine.strip()
        if len(trimmed) > 0 and trimmed[0] in ["-", "*", "+"]:
            return MarkdownLineType.ListItemUnordered

        # Geordnete Liste
        if self.is_ordered_list_item(sLine):
            return MarkdownLineType.ListItemOrdered

        # Blockquote
        if len(trimmed) > 0 and trimmed[0] == ">":
            return MarkdownLineType.Blockquote

        # Standard: Paragraph
        return MarkdownLineType.Paragraph

    def process_normal_line(self, sLine: str, lineType: MarkdownLineType) -> None:
        """Verarbeitet eine normale Zeile."""
        if MarkdownLineType.Heading1 <= lineType <= MarkdownLineType.Heading6:
            self.process_heading(sLine, lineType)
        elif lineType == MarkdownLineType.CodeBlockStart:
            self.start_code_block(sLine)
        elif lineType == MarkdownLineType.TableRow:
            self.start_table(sLine)
        elif lineType == MarkdownLineType.TableDelimiter:
            # Sollte nicht in Normal-State vorkommen
            self.process_content(sLine)
        elif lineType in [MarkdownLineType.ListItemOrdered, MarkdownLineType.ListItemUnordered]:
            self.process_list_item(sLine, lineType)
        elif lineType == MarkdownLineType.Blockquote:
            self.process_blockquote(sLine)
        elif lineType == MarkdownLineType.HorizontalRule:
            self.process_horizontal_rule()
        elif lineType == MarkdownLineType.FrontMatterDelimiter:
            if self.m_LineCounter == 1:
                self.m_ParserState = MarkdownParserState.InFrontMatter
            else:
                self.process_content(sLine)
        elif lineType == MarkdownLineType.EmptyLine:
            self.process_empty_line()
        else:
            self.process_content(sLine)

    def process_heading(self, sLine: str, headingLevel: MarkdownLineType) -> None:
        """Verarbeitet Überschriften."""
        # Überschriftentext extrahieren
        sHeadingText = self.extract_heading_text(sLine)

        # Neuen Knoten erstellen
        oNewNode = KnotObject()

        # Parent-Knoten basierend auf Level finden
        oParentNode = self.find_parent_for_heading(headingLevel)

        # Knoten initialisieren
        oNewNode.init("Heading", sHeadingText, oParentNode)

        # Metadaten hinzufügen
        oNewNode.m_Leafs["headingLevel"] = int(headingLevel)
        oNewNode.m_Leafs["lineNumber"] = self.m_LineCounter
        oNewNode.m_Leafs["content"] = ""

        # Zum Index hinzufügen
        if sHeadingText not in self.m_NodeIndex:
            self.m_NodeIndex[sHeadingText] = oNewNode

        # Als aktuellen Knoten setzen
        self.m_CurrentNode = oNewNode

        # Heading-Stack aktualisieren
        self.update_heading_stack(oNewNode, headingLevel)

    def find_parent_for_heading(self, headingLevel: MarkdownLineType) -> KnotObject:
        """Findet den passenden Parent-Knoten."""
        # Durch Heading-Stack gehen und passenden Parent finden
        for i in range(len(self.m_HeadingStack) - 1, -1, -1):
            oStackNode = self.m_HeadingStack[i]

            # Parent-Level aus Leafs holen
            if "headingLevel" in oStackNode.m_Leafs:
                parentLevel = oStackNode.m_Leafs["headingLevel"]
                if parentLevel < headingLevel:
                    return oStackNode

        # Kein passender Parent gefunden, Root verwenden
        return self._get_root_node()

    def update_heading_stack(self, oNode: KnotObject, headingLevel: MarkdownLineType) -> None:
        """Aktualisiert den Heading-Stack."""
        # Alle Knoten mit gleichem oder höherem Level entfernen
        i = len(self.m_HeadingStack) - 1
        while i >= 0:
            oStackNode = self.m_HeadingStack[i]

            if "headingLevel" in oStackNode.m_Leafs:
                stackLevel = oStackNode.m_Leafs["headingLevel"]
                if stackLevel >= headingLevel:
                    self.m_HeadingStack.pop(i)
                else:
                    break
            i -= 1

        # Neuen Knoten hinzufügen
        self.m_HeadingStack.append(oNode)

    def process_content(self, sLine: str) -> None:
        """Fügt Content zum aktuellen Knoten hinzu."""
        # Content zum aktuellen Knoten hinzufügen
        if self.m_CurrentNode is not None:
            nodeLeafs = self.m_CurrentNode.m_Leafs

            if "content" in nodeLeafs:
                currentContent = nodeLeafs["content"]
                if currentContent != "":
                    currentContent = currentContent + "\n"
                nodeLeafs["content"] = currentContent + sLine
            else:
                nodeLeafs["content"] = sLine

    def start_code_block(self, sLine: str) -> None:
        """Startet einen Code-Block."""
        # Sprache extrahieren (falls angegeben)
        if len(sLine) > 3:
            self.m_CodeBlockLanguage = sLine[3:].strip()
        else:
            self.m_CodeBlockLanguage = ""

        # Neuen Code-Block-Knoten erstellen
        oCodeNode = KnotObject()
        oCodeNode.init("CodeBlock", self.m_CodeBlockLanguage, self.m_CurrentNode)

        # Metadaten hinzufügen
        oCodeNode.m_Leafs["language"] = self.m_CodeBlockLanguage
        oCodeNode.m_Leafs["lineNumber"] = self.m_LineCounter
        oCodeNode.m_Leafs["content"] = ""

        # Parser-State ändern
        self.m_ParserState = MarkdownParserState.InCodeBlock
        self.m_CurrentNode = oCodeNode

    def process_code_block_line(self, sLine: str, lineType: MarkdownLineType) -> None:
        """Verarbeitet eine Code-Block-Zeile."""
        if lineType == MarkdownLineType.CodeBlockEnd:
            # Code-Block beenden
            self.m_ParserState = MarkdownParserState.Normal
            # Zum Parent zurückkehren
            if self.m_CurrentNode is not None and self.m_CurrentNode.m_oParent is not None:
                self.m_CurrentNode = self.m_CurrentNode.m_oParent
        else:
            # Code-Zeile hinzufügen
            self.process_content(sLine)

    def start_table(self, sLine: str) -> None:
        """Startet eine neue Tabelle."""
        # Parser-State ändern
        self.m_ParserState = MarkdownParserState.InTable

        # Tabellen-Daten zurücksetzen
        self.m_CurrentTableData = []
        self.m_TableHeaders = []

        # Header-Zeile parsen
        self.parse_table_row(sLine, self.m_TableHeaders)

    def process_table_line(self, sLine: str, lineType: MarkdownLineType) -> None:
        """Verarbeitet eine Tabellen-Zeile."""
        if lineType == MarkdownLineType.TableDelimiter:
            # Delimiter validieren (muss nach Header kommen)
            if len(self.m_TableHeaders) == 0:
                # Ungültige Tabelle, als normalen Text behandeln
                self.m_ParserState = MarkdownParserState.Normal
                self.process_content(sLine)
        elif lineType == MarkdownLineType.TableRow:
            # Datenzeile zur Sammlung hinzufügen
            rowData: List[str] = []
            self.parse_table_row(sLine, rowData)
            self.m_CurrentTableData.append(rowData)
        else:
            # Tabelle beenden und neue Zeile verarbeiten
            self.finalize_table()
            self.m_ParserState = MarkdownParserState.Normal
            self.process_normal_line(sLine, lineType)

    def parse_table_row(self, sLine: str, rowCollection: List[str]) -> None:
        """Parst eine Tabellen-Zeile."""
        # Zeile in Zellen aufteilen
        cells = sLine.split("|")

        # Leere Zellen am Anfang und Ende entfernen
        for i in range(len(cells)):
            cellContent = cells[i].strip()
            # Erste und letzte Zelle können leer sein (durch führende/abschließende |)
            if i > 0 and i < len(cells) - 1:
                rowCollection.append(cellContent)
            elif cellContent != "":
                rowCollection.append(cellContent)

    def finalize_table(self) -> None:
        """Erstellt ContainerInMemory aus Tabellendaten."""
        # Prüfen ob gültige Tabelle
        if len(self.m_TableHeaders) == 0 or len(self.m_CurrentTableData) == 0:
            return

        # ContainerInMemory erstellen
        oTableContainer = ContainerInMemory()
        oTableContainer.init_new(self.m_TableHeaders, f"Table_Line{self.m_LineCounter}")

        # Daten einfügen
        rowIndex = 1

        for rowData in self.m_CurrentTableData:
            # Neue Zeile hinzufügen
            oTableContainer.add_empty_row()

            # Zellen füllen
            colIndex = 0
            for cellValue in rowData:
                if colIndex < len(self.m_TableHeaders):
                    # Convert legacy NULL marker to Python None
                    actualValue: Optional[str] = None if cellValue == "##!empty!##" else cellValue
                    oTableContainer.set_value(rowIndex, self.m_TableHeaders[colIndex], actualValue)
                colIndex += 1

            rowIndex += 1

        # Tabellen-Knoten erstellen
        oTableNode = KnotObject()
        oTableNode.init("Table", f"Table_{self.m_LineCounter}", self.m_CurrentNode)

        # Container und Metadaten hinzufügen
        oTableNode.m_Leafs["container"] = oTableContainer
        oTableNode.m_Leafs["rowCount"] = len(self.m_CurrentTableData)
        oTableNode.m_Leafs["columnCount"] = len(self.m_TableHeaders)
        oTableNode.m_Leafs["lineNumber"] = self.m_LineCounter

        # Tabellen-Daten zurücksetzen
        self.m_CurrentTableData = []
        self.m_TableHeaders = []

    def finalize_open_structures(self) -> None:
        """Schließt alle offenen Strukturen ab."""
        # Offene Tabelle abschließen
        if self.m_ParserState == MarkdownParserState.InTable:
            self.finalize_table()

        # Parser-State zurücksetzen
        self.m_ParserState = MarkdownParserState.Normal

    def get_root_children(self) -> List[KnotObject]:
        """Gibt Collection der obersten Ebene zurück."""
        rootNodes: List[KnotObject] = []
        root = self._get_root_node()

        # Alle direkten Kinder des Root-Knotens sammeln
        for key in root.get_children().keys():
            rootNodes.append(root.get_child(key))

        return rootNodes

    def get_root_node(self) -> KnotObject:
        """Get root node."""
        return self._get_root_node()

    def find_node_by_title(self, sTitle: str) -> Optional[KnotObject]:
        """Sucht Knoten nach Überschrift."""
        # Erst im Index suchen
        if sTitle in self.m_NodeIndex:
            return self.m_NodeIndex[sTitle]

        # Wenn nicht gefunden, Baum durchsuchen
        return self.find_node_by_title_recursive(self._get_root_node(), sTitle)

    def find_node_by_title_recursive(self, oNode: KnotObject, sTitle: str) -> Optional[KnotObject]:
        """Rekursive Suche nach Titel."""
        # Aktuellen Knoten prüfen
        if oNode.m_vValue == sTitle:
            return oNode

        # Kinder durchsuchen
        for key in oNode.get_children().keys():
            result = self.find_node_by_title_recursive(oNode.get_child(key), sTitle)
            if result is not None:
                return result

        # Nichts gefunden
        return None

    def get_node_by_path(self, sPath: str) -> Optional[KnotObject]:
        """Navigiert über Pfad."""
        # Pfad in Teile aufteilen
        pathParts = sPath.split("/")

        # Vom Root aus navigieren
        currentNode: KnotObject = self._get_root_node()

        # Jeden Pfadteil durchgehen
        for i in range(len(pathParts)):
            found = False

            # In Kindern nach passendem Titel suchen
            for key in currentNode.get_children().keys():
                childNode = currentNode.get_child(key)
                if childNode.m_vValue == pathParts[i]:
                    currentNode = childNode
                    found = True
                    break

            # Wenn nicht gefunden, Nothing zurückgeben
            if not found:
                return None

        return currentNode

    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """Erstellt Inhaltsverzeichnis-Struktur."""
        toc: List[Dict[str, Any]] = []

        # Rekursiv durch Baum gehen
        self.add_node_to_toc(self._get_root_node(), toc, "")

        return toc

    def add_node_to_toc(self, oNode: KnotObject, toc: List[Dict[str, Any]], sIndent: str) -> None:
        """Fügt Knoten zum Inhaltsverzeichnis hinzu."""
        # Nur Überschriften zum TOC hinzufügen
        if oNode.m_sName == "Heading":
            tocEntry: Dict[str, Any] = {
                "title": oNode.m_vValue,
                "level": oNode.m_Leafs["headingLevel"],
                "indent": sIndent,
                "node": oNode
            }
            toc.append(tocEntry)

        # Kinder verarbeiten
        for key in oNode.get_children().keys():
            self.add_node_to_toc(oNode.get_child(key), toc, sIndent + "  ")

    def get_all_nodes_of_type(self, sNodeType: str) -> List[KnotObject]:
        """Findet alle Knoten eines bestimmten Typs."""
        nodes: List[KnotObject] = []

        # Rekursiv suchen
        self.find_nodes_of_type_recursive(self._get_root_node(), sNodeType, nodes)

        return nodes

    def find_nodes_of_type_recursive(self, oNode: KnotObject, sNodeType: str, nodes: List[KnotObject]) -> None:
        """Rekursive Suche nach Knotentyp."""
        # Aktuellen Knoten prüfen
        if oNode.m_sName == sNodeType:
            nodes.append(oNode)

        # Kinder durchsuchen
        for key in oNode.get_children().keys():
            self.find_nodes_of_type_recursive(oNode.get_child(key), sNodeType, nodes)

    def get_all_tables(self) -> List[ContainerInMemory]:
        """Gibt Collection aller ContainerInMemory-Tabellen zurück."""
        tables: List[ContainerInMemory] = []

        # Alle Table-Knoten finden
        tableNodes = self.get_all_nodes_of_type("Table")

        # Container extrahieren
        for node in tableNodes:
            if "container" in node.m_Leafs:
                tables.append(cast(ContainerInMemory, node.m_Leafs["container"]))

        return tables

    def get_node_content(self, oNode: KnotObject) -> str:
        """Holt formatierten Inhalt eines Knotens."""
        if "content" in oNode.m_Leafs:
            return cast(str, oNode.m_Leafs["content"])
        else:
            return ""

    def get_node_metadata(self, oNode: KnotObject) -> Dict[str, Any]:
        """Zugriff auf Knoten-Metadaten."""
        return oNode.m_Leafs

    def get_node_table(self, oNode: KnotObject) -> Optional[ContainerInMemory]:
        """Gibt ContainerInMemory zurück."""
        if oNode.m_sName == "Table" and "container" in oNode.m_Leafs:
            return cast(ContainerInMemory, oNode.m_Leafs["container"])
        else:
            return None

    def get_section_text(self, oNode: KnotObject, bIncludeSubsections: bool) -> str:
        """Gibt Text eines Abschnitts zurück."""
        sectionText = ""

        # Überschrift hinzufügen
        if oNode.m_sName == "Heading":
            level = oNode.m_Leafs["headingLevel"]
            sectionText = "#" * level + " " + oNode.m_vValue + "\n\n"

        # Content hinzufügen
        sectionText = sectionText + self.get_node_content(oNode)

        # Unterabschnitte hinzufügen wenn gewünscht
        if bIncludeSubsections:
            for key in oNode.get_children().keys():
                sectionText = sectionText + "\n\n"
                sectionText = sectionText + self.get_section_text(oNode.get_child(key), True)

        return sectionText

    def has_table(self, oNode: KnotObject) -> bool:
        """Prüft ob Knoten eine Tabelle enthält."""
        return oNode.m_sName == "Table" and "container" in oNode.m_Leafs

    def get_statistics(self) -> Dict[str, int]:
        """Gibt Dokumentstatistiken zurück."""
        stats = {
            "totalNodes": 0,
            "headingCount": 0,
            "tableCount": 0,
            "codeBlockCount": 0,
            "paragraphCount": 0,
            "totalWords": 0
        }

        # Rekursiv Statistiken sammeln
        self.collect_statistics_recursive(self._get_root_node(), stats)

        return stats

    def collect_statistics_recursive(self, oNode: KnotObject, stats: Dict[str, int]) -> None:
        """Sammelt Statistiken rekursiv."""
        # Gesamtzahl Knoten
        stats["totalNodes"] = stats["totalNodes"] + 1

        # Spezifische Zähler
        if oNode.m_sName == "Heading":
            stats["headingCount"] = stats["headingCount"] + 1
        elif oNode.m_sName == "Table":
            stats["tableCount"] = stats["tableCount"] + 1
        elif oNode.m_sName == "CodeBlock":
            stats["codeBlockCount"] = stats["codeBlockCount"] + 1
        elif oNode.m_sName == "Paragraph":
            stats["paragraphCount"] = stats["paragraphCount"] + 1

        # Wörter zählen
        if "content" in oNode.m_Leafs:
            content = oNode.m_Leafs["content"]
            stats["totalWords"] = stats["totalWords"] + self.count_words(content)

        # Kinder verarbeiten
        for key in oNode.get_children().keys():
            self.collect_statistics_recursive(oNode.get_child(key), stats)

    def count_words(self, sText: str) -> int:
        """Zählt Wörter in einem Text."""
        if sText.strip() == "":
            return 0

        # Mehrfache Leerzeichen durch einzelne ersetzen
        cleanText = sText.strip()
        while "  " in cleanText:
            cleanText = cleanText.replace("  ", " ")

        # Wörter zählen
        return len(cleanText.split(" "))

    def validate_structure(self) -> List[str]:
        """Prüft auf korrekte Hierarchie."""
        errors: List[str] = []

        # Rekursiv validieren
        self.validate_node_recursive(self._get_root_node(), errors, 0)

        return errors

    def validate_node_recursive(self, oNode: KnotObject, errors: List[str], expectedLevel: int) -> None:
        """Validiert Knoten rekursiv."""
        # Überschriften-Level prüfen
        if oNode.m_sName == "Heading":
            actualLevel = oNode.m_Leafs["headingLevel"]

            # Level sollte nicht mehr als 1 springen
            if actualLevel > expectedLevel + 1 and expectedLevel > 0:
                errors.append(f"Überschriften-Level springt von {expectedLevel} zu {actualLevel} bei: {oNode.m_vValue}")

        # Kinder validieren
        if oNode.m_sName == "Heading":
            childLevel = oNode.m_Leafs["headingLevel"]
        else:
            childLevel = expectedLevel

        for key in oNode.get_children().keys():
            self.validate_node_recursive(oNode.get_child(key), errors, childLevel)

    def get_heading_tree(self) -> List[Dict[str, Any]]:
        """Gibt Überschriftenbaum zurück."""
        tree: List[Dict[str, Any]] = []

        # Nur Überschriften sammeln
        self.build_heading_tree(self._get_root_node(), tree)

        return tree

    def build_heading_tree(self, oNode: KnotObject, tree: List[Dict[str, Any]]) -> None:
        """Baut Überschriftenbaum auf."""
        # Wenn es eine Überschrift ist, hinzufügen
        if oNode.m_sName == "Heading":
            treeNode: Dict[str, Any] = {
                "title": oNode.m_vValue,
                "level": oNode.m_Leafs["headingLevel"],
                "children": []
            }

            # Unterüberschriften sammeln
            for key in oNode.get_children().keys():
                self.build_heading_tree(oNode.get_child(key), cast(List[Dict[str, Any]], treeNode["children"]))

            tree.append(treeNode)
        else:
            # Keine Überschrift, aber Kinder könnten Überschriften sein
            for key2 in oNode.get_children().keys():
                self.build_heading_tree(oNode.get_child(key2), tree)

    def count_tables(self) -> int:
        """Zählt alle Tabellen im Dokument."""
        return len(self.get_all_nodes_of_type("Table"))

    def get_table_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken über Tabellen zurück."""
        stats: Dict[str, Any] = {
            "totalTables": 0,
            "totalRows": 0,
            "totalColumns": 0,
            "largestTable": 0,
            "smallestTable": 999999
        }

        # Alle Tabellen durchgehen
        tableNodes = self.get_all_nodes_of_type("Table")

        stats["totalTables"] = len(tableNodes)

        for node in tableNodes:
            if "rowCount" in node.m_Leafs:
                rowCount = node.m_Leafs["rowCount"]
                stats["totalRows"] = stats["totalRows"] + rowCount

                if rowCount > stats["largestTable"]:
                    stats["largestTable"] = rowCount
                if rowCount < stats["smallestTable"]:
                    stats["smallestTable"] = rowCount

            if "columnCount" in node.m_Leafs:
                stats["totalColumns"] = stats["totalColumns"] + node.m_Leafs["columnCount"]

        # Durchschnitte berechnen
        if stats["totalTables"] > 0:
            stats["avgRowsPerTable"] = stats["totalRows"] / stats["totalTables"]
            stats["avgColumnsPerTable"] = stats["totalColumns"] / stats["totalTables"]
        else:
            stats["smallestTable"] = 0
            stats["avgRowsPerTable"] = 0
            stats["avgColumnsPerTable"] = 0

        return stats

    # Hilfsfunktionen

    def get_heading_level(self, sLine: str) -> int:
        """Ermittelt das Heading-Level."""
        level = 0

        for i in range(len(sLine)):
            if sLine[i] == "#":
                level = level + 1
            else:
                break

        # Maximal 6 Level
        if level > 6:
            level = 0

        return level

    def extract_heading_text(self, sLine: str) -> str:
        """Extrahiert den Überschriftentext."""
        # # entfernen und trimmen
        text = sLine

        # Führende # entfernen
        while len(text) > 0 and text[0] == "#":
            text = text[1:]

        # Abschließende # entfernen (optional in Markdown)
        while len(text) > 0 and text[-1] == "#":
            text = text[:-1]

        return text.strip()

    def is_table_delimiter(self, sLine: str) -> bool:
        """Prüft ob Zeile eine Tabellen-Delimiter-Zeile ist."""
        # Muss | enthalten
        if "|" not in sLine:
            return False

        # Nur -, |, : und Leerzeichen erlaubt
        for i in range(len(sLine)):
            char = sLine[i]
            if char != "-" and char != "|" and char != ":" and char != " ":
                return False

        # Muss mindestens ein - enthalten
        return "-" in sLine

    def could_be_table_start(self, sLine: str) -> bool:
        """Prüft ob Zeile ein Tabellen-Start sein könnte."""
        # Muss | enthalten
        if "|" not in sLine:
            return False

        # Sollte mindestens 2 | haben (für mindestens 1 Spalte)
        pipeCount = 0
        for i in range(len(sLine)):
            if sLine[i] == "|":
                pipeCount = pipeCount + 1

        return pipeCount >= 2

    def is_ordered_list_item(self, sLine: str) -> bool:
        """Prüft ob Zeile ein geordnetes Listenelement ist."""
        trimmed = sLine.strip()

        # Muss mit Zahl beginnen
        if len(trimmed) < 3:
            return False

        # Erste Zeichen prüfen (1. 2. etc.)
        for i in range(len(trimmed) - 2):
            char = trimmed[i]
            if not char.isdigit():
                # Nach Zahlen muss . oder ) kommen
                if (char == "." or char == ")") and i > 0:
                    # Danach muss Leerzeichen kommen
                    if i + 1 < len(trimmed) and trimmed[i + 1] == " ":
                        return True
                return False

        return False

    def process_list_item(self, sLine: str, listType: MarkdownLineType) -> None:
        """Verarbeitet eine Listenzeile."""
        # Neuen Listen-Knoten erstellen wenn nötig
        if self.m_ParserState != MarkdownParserState.InList:
            self.m_ParserState = MarkdownParserState.InList

            listNode = KnotObject()

            if listType == MarkdownLineType.ListItemOrdered:
                listTypeName = "OrderedList"
            else:
                listTypeName = "UnorderedList"

            listNode.init(listTypeName, f"{listTypeName}_{self.m_LineCounter}", self.m_CurrentNode)
            listNode.m_Leafs["lineNumber"] = self.m_LineCounter
            self.m_CurrentNode = listNode

        # Listenelement hinzufügen
        itemNode = KnotObject()

        # Text extrahieren
        itemText = self.extract_list_item_text(sLine)

        itemNode.init("ListItem", itemText, self.m_CurrentNode)
        itemNode.m_Leafs["lineNumber"] = self.m_LineCounter
        itemNode.m_Leafs["content"] = ""

    def extract_list_item_text(self, sLine: str) -> str:
        """Extrahiert Text aus Listenelement."""
        text = sLine.strip()

        # Ungeordnete Liste
        if len(text) > 0 and text[0] in ["-", "*", "+"]:
            text = text[1:].strip()
        else:
            # Geordnete Liste - Nummer und Punkt/Klammer entfernen
            for i in range(len(text)):
                char = text[i]
                if char == "." or char == ")":
                    text = text[i + 1:].strip()
                    break

        return text

    def process_blockquote(self, sLine: str) -> None:
        """Verarbeitet eine Blockquote-Zeile."""
        # Neuen Blockquote-Knoten erstellen wenn nötig
        if self.m_ParserState != MarkdownParserState.InBlockquote:
            self.m_ParserState = MarkdownParserState.InBlockquote

            quoteNode = KnotObject()
            quoteNode.init("Blockquote", f"Blockquote_{self.m_LineCounter}", self.m_CurrentNode)
            quoteNode.m_Leafs["lineNumber"] = self.m_LineCounter
            quoteNode.m_Leafs["content"] = ""
            self.m_CurrentNode = quoteNode

        # > entfernen und als Content hinzufügen
        text = sLine.strip()
        if len(text) > 0 and text[0] == ">":
            text = text[1:].strip()

        self.process_content(text)

    def process_blockquote_line(self, sLine: str, lineType: MarkdownLineType) -> None:
        """Verarbeitet eine Blockquote-Zeile im Blockquote-Status."""
        if lineType == MarkdownLineType.Blockquote:
            self.process_blockquote(sLine)
        else:
            # Blockquote beenden
            self.m_ParserState = MarkdownParserState.Normal
            if self.m_CurrentNode is not None and self.m_CurrentNode.m_oParent is not None:
                self.m_CurrentNode = self.m_CurrentNode.m_oParent
            # Neue Zeile normal verarbeiten
            self.process_normal_line(sLine, lineType)

    def process_list_line(self, sLine: str, lineType: MarkdownLineType) -> None:
        """Verarbeitet eine Listen-Zeile im Listen-Status."""
        if lineType in [MarkdownLineType.ListItemOrdered, MarkdownLineType.ListItemUnordered]:
            self.process_list_item(sLine, lineType)
        elif lineType == MarkdownLineType.EmptyLine:
            # Leere Zeile könnte Liste beenden
            self.process_empty_line()
        else:
            # Liste beenden
            self.m_ParserState = MarkdownParserState.Normal
            if self.m_CurrentNode is not None and self.m_CurrentNode.m_oParent is not None:
                self.m_CurrentNode = self.m_CurrentNode.m_oParent
            # Neue Zeile normal verarbeiten
            self.process_normal_line(sLine, lineType)

    def process_horizontal_rule(self) -> None:
        """Verarbeitet eine horizontale Linie."""
        ruleNode = KnotObject()
        ruleNode.init("HorizontalRule", f"HorizontalRule_{self.m_LineCounter}", self.m_CurrentNode)
        ruleNode.m_Leafs["lineNumber"] = self.m_LineCounter

    def process_empty_line(self) -> None:
        """Verarbeitet eine leere Zeile."""
        # In Listen oder Blockquotes könnte dies das Ende bedeuten
        if self.m_ParserState in [MarkdownParserState.InList, MarkdownParserState.InBlockquote]:
            self.m_ParserState = MarkdownParserState.Normal
            if self.m_CurrentNode is not None and self.m_CurrentNode.m_oParent is not None:
                self.m_CurrentNode = self.m_CurrentNode.m_oParent

    def process_front_matter_line(self, sLine: str, lineType: MarkdownLineType) -> None:
        """Verarbeitet eine Frontmatter-Zeile."""
        if lineType == MarkdownLineType.FrontMatterDelimiter:
            # Frontmatter beenden
            self.m_ParserState = MarkdownParserState.Normal
        else:
            # YAML-ähnliche Key-Value Paare parsen
            if ":" in sLine:
                parts = sLine.split(":", 1)
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = parts[1].strip()

                    if key not in self.m_Metadata:
                        self.m_Metadata[key] = value

    def get_metadata(self) -> Dict[str, Any]:
        """Gibt die Metadaten des Dokuments zurück."""
        return self.m_Metadata

    def clean_up(self) -> None:
        """Bereinigt Speicher und gibt Ressourcen frei."""
        # ContainerInMemory-Objekte freigeben
        tableNodes = self.get_all_nodes_of_type("Table")

        for node in tableNodes:
            if "container" in node.m_Leafs:
                container = node.m_Leafs["container"]
                container.purge_memory()

        # KnotObject-Struktur dekonstruieren
        if self.m_RootNode is not None:
            self.m_RootNode.deconstruct()

        # Alle Objekte freigeben
        self.m_RootNode = None
        self.m_CurrentNode = None
        self.m_NodeIndex = {}
        self.m_HeadingStack = []
        self.m_Metadata = {}
        self.m_CurrentTableData = []
        self.m_TableHeaders = []

        log_msg("MarkdownDocument-Ressourcen wurden freigegeben.")

    def create_table_dictionary(self) -> Dict[str, ContainerInMemory]:
        """
        Erstellt ein Dictionary mit Tabellennamen als Schlüssel und ContainerInMemory als Werte.
        """
        oTableDict: Dict[str, ContainerInMemory] = {}

        # Alle Table-Knoten aus dem Dokument abrufen
        oTableNodes = self.get_all_nodes_of_type("Table")

        log_msg(f"Gefundene Table-Knoten: {len(oTableNodes)}")  # Debug-Ausgabe

        # Durch alle gefundenen Tabellen iterieren
        for i in range(len(oTableNodes)):
            oTableNode = oTableNodes[i]

            # Den Parent-Knoten (die Überschrift) ermitteln
            oParentNode = oTableNode.m_oParent

            # Prüfen ob Parent vorhanden und vom Typ Heading ist
            if oParentNode is not None:
                if oParentNode.m_sName == "Heading":
                    # Tabellennamen aus der Überschrift extrahieren
                    sHeadingText = oParentNode.m_vValue

                    # HIER IST DIE ÄNDERUNG:
                    # Prüfen ob die Überschrift mit "Table: " beginnt
                    if sHeadingText[:7] == "Table: ":
                        # Tabellennamen ohne Präfix extrahieren
                        sTableName = sHeadingText[7:]
                    else:
                        # NEUE LOGIK: Direkt den Überschriftstext als Tabellennamen verwenden
                        sTableName = sHeadingText

                    # ContainerInMemory-Objekt abrufen
                    oContainer = self.get_node_table(oTableNode)

                    # Prüfen ob Container erfolgreich abgerufen wurde
                    if oContainer is not None:
                        # Zum Dictionary hinzufügen, falls noch nicht vorhanden
                        if sTableName not in oTableDict:
                            oTableDict[sTableName] = oContainer
                            # log_msg(f"Tabelle '{sTableName}' zum Dictionary hinzugefuegt.")
                        else:
                            log_msg(f"Warnung: Tabelle '{sTableName}' existiert bereits im Dictionary.")
                    else:
                        log_msg(f"Warnung: Kein ContainerInMemory fuer Tabelle unter Ueberschrift '{sHeadingText}' gefunden.")
                else:
                    log_msg(f"Warnung: Parent-Knoten ist keine Ueberschrift, sondern vom Typ '{oParentNode.m_sName}'")
            else:
                log_msg("Warnung: Table-Knoten ohne Parent-Knoten gefunden.")

        # Ergebnis-Dictionary zurückgeben
        log_msg(f"Tabellen-Dictionary erstellt mit {len(oTableDict)} Eintraegen.")
        return oTableDict
