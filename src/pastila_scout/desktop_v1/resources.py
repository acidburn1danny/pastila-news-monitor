"""Immutable Romanian resources for the desktop shell."""

from pastila_scout import __version__

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
    ("navigation.chief_editor", "Chief Editor"),
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
    ("scout.send_editor", "Trimite în Editor"),
    ("scout.no_candidates", "Nu există materiale Scout disponibile."),
    ("scout.handoff_success", "Materialul a fost trimis în Editor."),
    ("scout.handoff_failure", "Materialul nu a putut fi trimis în Editor."),
    ("editor.title", "Editor"),
    ("editor.active_project", "Proiect activ"),
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
    ("chief_editor.title", "Titlu episod / proiect"),
    ("chief_editor.section", "Secțiune"),
    ("chief_editor.note", "Notă / tranziție"),
    ("chief_editor.up", "Sus"),
    ("chief_editor.add", "Adaugă"),
    ("chief_editor.down", "Jos"),
    ("chief_editor.remove", "Elimină din structură"),
    ("chief_editor.save", "Salvează"),
    ("chief_editor.export", "Exportă structura"),
    ("chief_editor.empty", "Nu există materiale dezvoltate în Editor."),
    ("chief_editor.saved", "Structura Chief Editor a fost salvată."),
    ("about.title", "Despre Pastila Scout"),
    ("about.body", "Pastila Scout"),
    ("about.version", __version__),
    ("close.running", "Închidere în curs…"),
    ("error.internal", "Aplicația a întâmpinat o eroare internă."),
    ("startup.error", "Aplicația nu a putut fi configurată."),
    ("state.error", "Starea aplicației Windows nu a putut fi inițializată."),
    ("migration.title", "Importă starea de dezvoltare"),
    (
        "migration.prompt",
        "Selectați un proiect de dezvoltare pentru import. Fișierele sursă nu vor fi șterse.",
    ),
    ("migration.confirm", "Importați starea validată în profilul Windows?"),
    ("migration.error", "Starea de dezvoltare nu a putut fi importată."),
    ("sources.override.error", "Configurația surselor personalizate este invalidă."),
)
_LOOKUP = dict(_TEXT_V1)
if len(_LOOKUP) != len(_TEXT_V1):
    raise RuntimeError("Duplicate desktop resource key")


def _text_v1(*, key: str) -> str:
    if type(key) is not str or key not in _LOOKUP:
        raise _DesktopShellConfigurationError() from None
    return _LOOKUP[key]
