"""Immutable Romanian resources for the desktop shell."""

from .errors import _DesktopShellConfigurationError

_TEXT_V1 = (
    ("app.title", "Pastila Scout"),
    ("menu.file", "Fișier"),
    ("menu.file.exit", "Ieșire"),
    ("menu.view", "Vizualizare"),
    ("menu.view.scout", "Scout"),
    ("menu.view.editor", "Editor"),
    ("menu.help", "Ajutor"),
    ("menu.help.about", "Despre"),
    ("menu.help.check_updates", "Caută actualizări"),
    ("navigation.scout", "Scout"),
    ("navigation.editor", "Editor"),
    ("scout.period", "PERIOADA"),
    ("scout.category", "CATEGORIA"),
    ("scout.run", "CAUTĂ"),
    ("scout.results", "REZULTATE"),
    ("scout.intro", "Selectați perioada și categoria, apoi apăsați „CAUTĂ”."),
    ("scout.progress.reading", "Pastila citește ziarele…"),
    ("scout.progress.verifying", "verifică și compară…"),
    ("scout.progress.writing", "scrie raportul pentru șefu’…"),
    ("scout.progress.ready", "Gata, șefu’! Raportul este pregătit."),
    ("scout.failed_sources", "Surse nereușite"),
    ("scout.report", "Deschide raportul"),
    ("editor.title", "Editor"),
    ("editor.unavailable", "Editorul va fi disponibil într-o etapă ulterioară."),
    ("editor.scout_input", "Intrare Scout"),
    ("editor.selection_profile", "Profil de selecție"),
    ("editor.episode_context", "Context episod"),
    ("editor.generation_config", "Configurație generare"),
    ("editor.provider", "Furnizor"),
    ("editor.model", "Model"),
    ("editor.timeout", "Timp-limită (secunde)"),
    ("editor.output", "Fișier de ieșire"),
    ("editor.no_replace", "Nu înlocui fișierul existent"),
    ("editor.run", "GENEREAZĂ"),
    ("about.title", "Despre Pastila Scout"),
    ("about.body", "Pastila Scout"),
    ("close.running", "Închidere în curs…"),
    ("error.internal", "Aplicația a întâmpinat o eroare internă."),
)
_LOOKUP = dict(_TEXT_V1)
if len(_LOOKUP) != len(_TEXT_V1):
    raise RuntimeError("Duplicate desktop resource key")


def _text_v1(*, key: str) -> str:
    if type(key) is not str or key not in _LOOKUP:
        raise _DesktopShellConfigurationError() from None
    return _LOOKUP[key]
