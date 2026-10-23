"""Interface de linha de comando do Modpack Fixer (Fase 1).

Uso exemplos:

    # Resolver dependências e criar pack local
    python -m modpack_fixer resolve \
        --mods create,jei,roughlyenoughitems \
        --game-version 1.20.1 --loader fabric \
        --name "Meu Pack de Teste" --output ./pack

    # Exportar .mrpack a partir do lockfile gerado
    python -m modpack_fixer export \
        --lockfile ./pack/lockfile.json --output ./pack.mrpack
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .export import export_mrpack
from .lockfile import save_lockfile
from .metadata import ModrinthClient
from .solver import Solver, SolverError


def cmd_resolve(args: argparse.Namespace) -> int:
    client = ModrinthClient()
    solver = Solver(client)

    mods = [m.strip() for m in args.mods.split(",") if m.strip()]
    try:
        result = solver.resolve(
            root_mods=mods,
            game_version=args.game_version,
            loader=args.loader,
            pack_name=args.name,
        )
    except SolverError as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.output)
    lock_path = save_lockfile(result.lockfile, out_dir)

    print(f"[OK] {len(result.lockfile.mods)} mods resolvidos para '{args.name}'.")
    for warning in result.warnings:
        print(f"[AVISO] {warning}")
    print(f"Lockfile salvo em: {lock_path}")
    print("Próximo passo: python -m modpack_fixer export --lockfile ./pack/lockfile.json --output ./pack.mrpack")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    export_mrpack(args.lockfile, Path(args.output))
    print(f"[OK] .mrpack exportado em: {args.output}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    from .search import auto_select, unified_search

    client = ModrinthClient()
    results = unified_search(
        args.query,
        client,
        limit=args.limit,
        game_version=args.game_version,
        loader=args.loader,
    )

    if not results:
        print("Nenhum resultado encontrado.")
        return 1

    print(f"\nResultados para '{args.query}':\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r.source}] {r.title}")
        print(f"   slug: {r.slug or '(não identificado)'}")
        print(f"   url: {r.url}")
        if r.description:
            print(f"   desc: {r.description[:140]}")
        print(f"   downloads: {r.downloads} | follows: {r.follows}")
        if r.game_versions:
            print(f"   game_versions: {', '.join(r.game_versions[:5])}")
        if r.loaders:
            print(f"   loaders: {', '.join(r.loaders)}")
        print()

    top = auto_select(results)
    if top:
        print(f"Sugestão para resolver automaticamente: {top.slug}")
        print(
            "Exemplo: python -m modpack_fixer resolve "
            f"--mods {top.slug} --game-version {args.game_version or '1.20.1'} "
            f"--loader {args.loader or 'fabric'}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mpfix",
        description="Modpack Fixer — solver determinístico + lockfile para Minecraft (Modrinth)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve", help="Resolver dependências e gerar lockfile local")
    p_resolve.add_argument("--mods", required=True, help="Slugs Modrinth separados por vírgula (ex: create,jei)")
    p_resolve.add_argument("--game-version", required=True, help="Versão do Minecraft (ex: 1.20.1)")
    p_resolve.add_argument("--loader", required=True, choices=["forge", "fabric", "quilt", "neoforge"])
    p_resolve.add_argument("--name", default="Meu Pack", help="Nome do pack")
    p_resolve.add_argument("--output", default="./pack", help="Diretório de saída do pack")
    p_resolve.set_defaults(func=cmd_resolve)

    p_export = sub.add_parser("export", help="Exportar .mrpack a partir de um lockfile")
    p_export.add_argument("--lockfile", required=True, help="Caminho para lockfile.json")
    p_export.add_argument("--output", required=True, help="Caminho de saída do .mrpack")
    p_export.set_defaults(func=cmd_export)

    p_search = sub.add_parser("search", help="Buscar mods na Modrinth + DuckDuckGo")
    p_search.add_argument("--query", required=True, help="Termo de busca (ex: automacao fabric 1.20.1)")
    p_search.add_argument("--limit", type=int, default=10, help="Máximo de resultados")
    p_search.add_argument("--game-version", default=None, help="Filtrar por versão do Minecraft")
    p_search.add_argument("--loader", default=None, choices=["forge", "fabric", "quilt", "neoforge"])
    p_search.set_defaults(func=cmd_search)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
