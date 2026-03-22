"""
INI Configuration File Reader

Diese Klasse ermöglicht das Lesen und den Zugriff auf Parameter aus INI-Dateien.
Entspricht PEP8 Standards und verwendet Type-Hints.
"""

import configparser
from pathlib import Path
from typing import Dict, List, Optional, Union

from .logging import log_and_raise, log_msg

# Forward import to avoid circular dependency


class IniConfigFile:
    """
    Eine Klasse zum Lesen und Verwalten von INI-Konfigurationsdateien.
    
    Attributes:
        file_path (Path): Pfad zur INI-Datei
        config (configparser.ConfigParser): ConfigParser Instanz
    """
    
    def __init__(self, file_path: Union[str, Path]):
        """
        Initialisiert die IniConfigFile Klasse mit einer INI-Datei.
        
        Args:
            file_path: Pfad zur INI-Datei
            
        Raises:
            FileNotFoundError: Wenn die Datei nicht existiert
            configparser.Error: Bei Parsing-Fehlern
        """
        self.file_path = Path(file_path)
        self.config = configparser.ConfigParser()
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {self.file_path}")
            #log_and_raise(f"Konfigurationsdatei nicht gefunden: {self.file_path}")

        try:
            self.config.read(self.file_path, encoding='utf-8')
        except configparser.Error as e:
            msg = f"Fehler beim Parsen der INI-Datei: {e}"
            log_and_raise(msg)
            raise configparser.Error(msg)

        # Validiere parent_section Referenzen nach dem Laden
        self._validate_parent_sections()
    
    def get_sections(self) -> List[str]:
        """
        Gibt alle verfügbaren Sektionen zurück.
        
        Returns:
            Liste aller Sektionen in der INI-Datei
        """
        return self.config.sections()
    
    def has_section(self, section: str) -> bool:
        """
        Prüft, ob eine Sektion existiert.
        
        Args:
            section: Name der zu prüfenden Sektion
            
        Returns:
            True wenn die Sektion existiert, False andernfalls
        """
        return self.config.has_section(section)
    
    def get_options(self, section: str) -> List[str]:
        """
        Gibt alle Optionen einer Sektion zurück.
        
        Args:
            section: Name der Sektion
            
        Returns:
            Liste aller Optionen in der Sektion
            
        Raises:
            configparser.NoSectionError: Wenn die Sektion nicht existiert
        """
        if not self.has_section(section):
            raise configparser.NoSectionError(f"Sektion '{section}' nicht gefunden")
        
        return self.config.options(section)
    
    def has_option(self, option: str, section: str) -> bool:
        """
        Prüft, ob eine Option in einer Sektion existiert.
        
        Args:
            section: Name der Sektion
            option: Name der Option
            
        Returns:
            True wenn die Option existiert, False andernfalls
        """
        return self.config.has_option(section, option)
    
    def get_value(self, option: str, section: str, must_exist: bool= True) -> Optional[str]:
        """
        Gibt den Wert einer Option als String zurück mit hierarchischer Vererbung.

        Args:
            option: Name der Option
            section: Name der Sektion
            must_exist: Ob der Parameter existieren muss

        Returns:
            Wert der Option als String oder None

        Raises:
            configparser.NoSectionError: Wenn die Sektion nicht existiert
            configparser.NoOptionError: Wenn die Option nicht existiert und must_exist=True
        """

        try:
            # Prüfe ob die angegebene Sektion existiert
            if not self.has_section(section):
                raise configparser.NoSectionError(f"Sektion '{section}' nicht gefunden")

            # Durchlaufe die Vererbungskette
            inheritance_chain = self._get_inheritance_chain(section)

            for current_section in inheritance_chain:
                if self.has_option(option, current_section):
                    result = self.config.get(current_section, option)

                    # Logge wenn wir zu einer parent_section gewechselt sind
                    if current_section != section:
                        log_msg(f"Parameter '{option}' nicht in Sektion '{section}' gefunden, verwende Wert aus Sektion '{current_section}': {result}")

                    return result

            # Parameter wurde in der gesamten Vererbungskette nicht gefunden
            if must_exist:
                chain_str = ' -> '.join(inheritance_chain)
                log_and_raise(f"Muss-Parameter '{option}' existiert nicht in der Vererbungskette der Sektionen: {chain_str}")
                raise configparser.NoOptionError(option, section)
            else:
                chain_str = ' -> '.join(inheritance_chain)
                log_msg(f"Optionaler Parameter '{option}' nicht in der Vererbungskette gefunden: {chain_str}")
                return None

        except configparser.NoSectionError as e:
            log_and_raise(f"Sektion fehlt: {section}")
            raise e
        except configparser.NoOptionError as e:
            log_and_raise(f"Parameter fehlt: {option} in Sektion {section}")
            raise e
    
    def get_int_value(self, option: str, section: str,must_exist: bool= True) -> Optional[int]:
        value = self.get_value(option, section, must_exist)
        if value is None:
            return None
        else:
            return int(value)

    def get_float_value(self, option: str, section: str, must_exist: bool = True) -> Optional[float]:
        """
        Gibt den Wert einer Option als Float zurück mit hierarchischer Vererbung.

        Args:
            option: Name der Option
            section: Name der Sektion
            must_exist: Ob der Parameter existieren muss

        Returns:
            Wert der Option als Float oder None

        Raises:
            ValueError: Wenn der Wert nicht in einen Float konvertiert werden kann
            configparser.NoSectionError: Wenn die Sektion nicht existiert
            configparser.NoOptionError: Wenn die Option nicht existiert und must_exist=True
        """
        value = self.get_value(option, section, must_exist)
        if value is None:
            return None
        else:
            try:
                return float(value)
            except ValueError:
                msg = f"Der Wert '{value}' von {option} in der Sektion {section} kann nicht in einen Float konvertiert werden."
                log_and_raise(msg)
                raise ValueError(msg)

    def get_bool_value(self, option: str, section: str, must_exist: bool= True) -> Optional[bool]:
        value = self.get_value(option, section, must_exist)
        if value is None:
            return None
        else:
            if value.lower() in ('true', 'wahr', 'yes', 'ja', '1'):
                return True
            else:
                if value.lower() in ('false', 'falsch', 'no', 'nein', '0'):
                    return False
                else:
                    msg = f"der Wert von {option} in der Sektion {section} ist kein boolscher Wert."
                    log_and_raise(msg)
                    raise ValueError(msg)

                

    def get_section_dict(self, section: str) -> Dict[str, str]:
        """
        Gibt alle Optionen einer Sektion als Dictionary zurück.
        
        Args:
            section: Name der Sektion
            
        Returns:
            Dictionary mit allen Optionen und Werten der Sektion
            
        Raises:
            configparser.NoSectionError: Wenn die Sektion nicht existiert
        """
        if not self.has_section(section):
            raise configparser.NoSectionError(f"Sektion '{section}' nicht gefunden")
        
        return dict(self.config.items(section))
    
    def get_all_config(self) -> Dict[str, Dict[str, str]]:
        """
        Gibt die komplette Konfiguration als verschachteltes Dictionary zurück.
        
        Returns:
            Dictionary mit allen Sektionen und deren Optionen
        """
        result: Dict[str, Dict[str, str]] = {}
        for section in self.get_sections():
            result[section] = self.get_section_dict(section)
        return result
    
    def reload(self) -> None:
        """
        Lädt die Konfigurationsdatei neu.

        Raises:
            FileNotFoundError: Wenn die Datei nicht mehr existiert
            configparser.Error: Bei Parsing-Fehlern
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {self.file_path}")

        self.config.clear()
        try:
            self.config.read(self.file_path, encoding='utf-8')
        except configparser.Error as e:
            raise configparser.Error(f"Fehler beim Parsen der INI-Datei: {e}")

        # Validiere parent_section Referenzen nach dem Neuladen
        self._validate_parent_sections()
    
    def __str__(self) -> str:
        """String-Repräsentation der Klasse."""
        return f"IniConfigFile('{self.file_path}', sections={len(self.get_sections())})"
    
    def __repr__(self) -> str:
        """Offizielle String-Repräsentation der Klasse."""
        return f"IniConfigFile(file_path=Path('{self.file_path}'))"

    def _validate_parent_sections(self) -> None:
        """
        Validiert alle parent_section Referenzen auf Existenz und zirkuläre Referenzen.

        Raises:
            ValueError: Bei nicht-existenten parent_sections oder zirkulären Referenzen
        """
        for section in self.get_sections():
            if self.has_option('parent_section', section):
                parent = self.config.get(section, 'parent_section')

                # Prüfe ob parent_section existiert
                if not self.has_section(parent):
                    msg = f"parent_section '{parent}' in Sektion '{section}' existiert nicht"
                    log_and_raise(msg)

                # Prüfe auf zirkuläre Referenzen
                visited: set[str] = set()
                current = section
                path: List[str] = []

                while current and self.has_option('parent_section', current):
                    if current in visited:
                        cycle_path = ' -> '.join(path + [current])
                        msg = f"Zirkuläre Referenz in parent_section gefunden: {cycle_path}"
                        log_and_raise(msg)

                    visited.add(current)
                    path.append(current)
                    current = self.config.get(current, 'parent_section')

    def _get_inheritance_chain(self, section: str) -> List[str]:
        """
        Gibt die komplette Vererbungskette für eine Sektion zurück.

        Args:
            section: Name der Sektion

        Returns:
            Liste der Sektionen in der Vererbungskette (von aktuell zu Wurzel)
        """
        chain: List[str] = []
        current = section

        while current:
            chain.append(current)
            if self.has_section(current) and self.has_option('parent_section', current):
                current = self.config.get(current, 'parent_section')
            else:
                break

        # Füge 'default' als finalen Fallback hinzu, wenn es existiert
        if 'default' not in chain and self.has_section('default'):
            chain.append('default')

        return chain
