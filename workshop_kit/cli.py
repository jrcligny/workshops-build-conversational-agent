
"""CLI : atelier verifier, verifier --non-regression, verifier-coquille, commencer."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

ATELIERS = [
    "03", "04", "05", "06", "07", "08", "09",
    "10a", "10b", "10c", "10d",
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
]


def ordre() -> list[str]:
    return list(ATELIERS)


def precedents(inclus: str) -> list[str]:
    if inclus not in ATELIERS:
        raise SystemExit(f"atelier inconnu : {inclus}")
    return ATELIERS[: ATELIERS.index(inclus) + 1]


def dossier_tests(identifiant: str) -> Path:
    return RACINE / "tests" / f"atelier-{identifiant}"


def _pytest(dossiers: list[Path], extra: list[str] | None = None) -> int:
    args = [sys.executable, "-m", "pytest", *[str(d) for d in dossiers], *(extra or [])]
    return subprocess.call(args, cwd=RACINE)


def cmd_verifier(identifiant: str, non_regression: bool) -> int:
    ids = precedents(identifiant) if non_regression else [identifiant]
    manquants = [i for i in ids if not dossier_tests(i).is_dir()]
    if manquants:
        print(f"dossiers de tests manquants : {', '.join(manquants)}", file=sys.stderr)
        return 2
    print(f"Vérification des ateliers : {', '.join(ids)}")
    return _pytest([dossier_tests(i) for i in ids], ["-m", "atelier"])


def cmd_verifier_coquille() -> int:
    """Succès (code 0) si tous les tests d'atelier échouent ou sont en erreur, et qu'aucun ne passe."""
    dossiers = [dossier_tests(i) for i in ATELIERS if dossier_tests(i).is_dir()]
    if not dossiers:
        print("aucun dossier tests/atelier-* trouvé", file=sys.stderr)
        return 2
    rapport = RACINE / ".pytest_coquille.xml"
    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            *[str(d) for d in dossiers],
            "-m", "atelier",
            "-q",
            "--tb=no",
            "--color=no",
            f"--junitxml={rapport}",
        ],
        cwd=RACINE,
        capture_output=True,
        text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return _interpreter_coquille(proc.returncode, (proc.stdout or "") + (proc.stderr or ""), rapport)


def _interpreter_coquille(code: int, sortie: str, rapport: Path | None = None) -> int:
    """0 si tout a échoué comme prévu, 1 sinon."""
    import re
    import xml.etree.ElementTree as ET

    passed = failed = errors = collected = 0
    if rapport and rapport.exists():
        root = ET.parse(rapport).getroot()
        # pytest may emit a <testsuites> wrapper or a bare <testsuite>.
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        for suite in suites:
            collected += int(suite.attrib.get("tests") or 0)
            failed += int(suite.attrib.get("failures") or 0)
            errors += int(suite.attrib.get("errors") or 0)
            skipped = int(suite.attrib.get("skipped") or 0)
            passed += max(collected - failed - errors - skipped, 0)
            # If several suites, "passed" must be recomputed globally below.
        if len(suites) > 1:
            collected = failed = errors = skipped_total = 0
            for suite in suites:
                collected += int(suite.attrib.get("tests") or 0)
                failed += int(suite.attrib.get("failures") or 0)
                errors += int(suite.attrib.get("errors") or 0)
                skipped_total += int(suite.attrib.get("skipped") or 0)
            passed = max(collected - failed - errors - skipped_total, 0)
        elif suites:
            suite = suites[0]
            skipped = int(suite.attrib.get("skipped") or 0)
            collected = int(suite.attrib.get("tests") or 0)
            failed = int(suite.attrib.get("failures") or 0)
            errors = int(suite.attrib.get("errors") or 0)
            passed = max(collected - failed - errors - skipped, 0)
    if collected == 0:
        m = re.search(r"(\d+) passed", sortie)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", sortie)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+) error", sortie)
        if m:
            errors = int(m.group(1))
        m = re.search(r"collected (\d+) item", sortie)
        if m:
            collected = int(m.group(1))
    if collected == 0 and (failed + passed + errors) == 0:
        print("aucun test d'atelier collecté", file=sys.stderr)
        return 2
    total_echec = failed + errors
    print(
        f"Coquille vide : {passed} test(s) passé(s), {failed} échec(s), {errors} erreur(s) "
        f"(collectés : {collected or failed + passed + errors})."
    )
    if passed > 0:
        print(
            "ERREUR : au moins un test d'atelier passe sur la coquille vide. "
            "Tous doivent échouer tant que l'atelier n'est pas réalisé.",
            file=sys.stderr,
        )
        return 1
    if total_echec == 0:
        print("ERREUR : aucun test d'atelier n'a échoué.", file=sys.stderr)
        return 1
    print("Comportement attendu : tous les tests d'atelier échouent sur la coquille vide.")
    return 0


def cmd_commencer(identifiant: str) -> int:
    if identifiant not in ATELIERS:
        raise SystemExit(f"atelier inconnu : {identifiant}")
    guide = RACINE / "ateliers" / _nom_guide(identifiant) / "GUIDE.md"
    print(f"Atelier {identifiant}. Aucun corrigé n'est copié : vous travaillez dans mon-agent/.")
    if guide.exists():
        print(f"Guide : {guide.relative_to(RACINE)}")
    print("Lancez les applications (voir docs/installation.md), puis :")
    print(f"  atelier verifier {identifiant}")
    if not (RACINE / "mon-agent" / "harness.py").exists():
        print("Attention : mon-agent/harness.py est absent.", file=sys.stderr)
        return 2
    return 0


def _nom_guide(identifiant: str) -> str:
    noms = {
        "03": "03-system-prompt",
        "04": "04-premier-outil",
        "05": "05-outils-lecture",
        "06": "06-boucle-agentique",
        "07": "07-contexte-compaction",
        "08": "08-memoire-travail",
        "09": "09-mcp",
        "10a": "10a-identite",
        "10b": "10b-ecritures",
        "10c": "10c-regroupements",
        "10d": "10d-confinement",
        "11": "11-architecture",
        "12": "12-memoire-longue",
        "13": "13-recherche-documentaire",
        "14": "14-skills",
        "15": "15-lire-sans-obeir",
        "16": "16-controles",
        "17": "17-evaluation",
        "18": "18-pannes",
        "19": "19-specification",
    }
    return noms.get(identifiant, identifiant)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atelier", description="Outils des ateliers du dépôt compagnon.")
    sous = parser.add_subparsers(dest="commande", required=True)

    v = sous.add_parser("verifier", help="Lancer les tests d'un atelier")
    v.add_argument("identifiant")
    v.add_argument("--non-regression", action="store_true", help="Inclure les ateliers précédents")

    sous.add_parser("verifier-coquille", help="Vérifier que tous les tests d'atelier échouent sur la coquille vide")

    c = sous.add_parser("commencer", help="Rappeler le guide, sans copier de code d'agent")
    c.add_argument("identifiant")

    args = parser.parse_args(argv)
    if args.commande == "verifier":
        return cmd_verifier(args.identifiant, args.non_regression)
    if args.commande == "verifier-coquille":
        return cmd_verifier_coquille()
    if args.commande == "commencer":
        return cmd_commencer(args.identifiant)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
