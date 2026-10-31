
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class CmsTypes:
    drupal: str = "Drupal"
    drupal_detect: str = "core/lib/Drupal.php"
    drupal_checked_subdirs: list[str] = field(default_factory=list[str])

    joomla: str = "Joomla"
    joomla_detect: str = "configuration.php"
    joomla_checked_subdirs: list[str] = field(
        default_factory=lambda: ["images", "tmp"])

    mediawiki: str = "Mediawiki"
    mediawiki_detect: str = "LocalSettings.php"
    mediawiki_checked_subdirs: list[str] = field(
        default_factory=lambda: ["images"])

    wordpress: str = "Wordpress"
    wordpress_detect: str = "wp-settings.php"
    wordpress_checked_subdirs: list[str] = field(
        default_factory=lambda: ["wp-content/uploads"])

    unknown: str = "UnknownPHP"
    unknown_php_detect: str = "php"
    static: str = "Static"

@dataclass
class CmsPaths:
    drupal_sites: list[Path] = field(default_factory=list[Path])
    joomla_sites: list[Path] = field(default_factory=list[Path])
    mediawiki_sites: list[Path] = field(default_factory=list[Path])
    wordpress_sites: list[Path] = field(default_factory=list[Path])
    static_sites: list[Path] = field(default_factory=list[Path])
    unknown_php_sites: list[Path] = field(default_factory=list[Path])
