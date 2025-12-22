from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gx_compat import try_import_great_expectations

gx, _GX_IMPORT_ERROR = try_import_great_expectations()


def main() -> None:
    if gx is None:
        print(f"Great Expectations failed to import. Details: {_GX_IMPORT_ERROR}")
        return

    repo_root = Path(__file__).resolve().parents[1]

    # Create or load a FileDataContext rooted at repo
    context = gx.get_context(project_root_dir=repo_root, mode="file")

    # Configure a docs site (writes to a directory)
    docs_site_config = {
        "class_name": "SiteBuilder",
        "site_index_builder": {"class_name": "DefaultSiteIndexBuilder"},
        "store_backend": {
            "class_name": "TupleFilesystemStoreBackend",
            "base_directory": str(repo_root / "artifacts" / "data_docs"),
        },
    }

    # Make the config idempotent
    if not hasattr(context, "add_data_docs_site"):
        # GX versions vary; if this is missing, rely on great_expectations.yml defaults.
        return

    try:
        context.add_data_docs_site(site_name="local_site", site_config=docs_site_config)
    except Exception:
        # If already exists, update it.
        context.update_data_docs_site(site_name="local_site", site_config=docs_site_config)


if __name__ == "__main__":
    main()
