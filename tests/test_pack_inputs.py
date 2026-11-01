"""Finite pack manifests: pure validation and private-file loader tests, no native calls."""
import copy
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
import urllib.request  # Load stdlib socket-derived classes before socket is mocked.
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("books_pack_inputs_under_test", ROOT / "scripts/build_native.py")
_build = importlib.util.module_from_spec(_spec)
# Importing validation must never initialize the native bootstrap or spawn a child.
with patch.object(ctypes, "WinDLL", side_effect=AssertionError("native import"), create=True), \
     patch.object(subprocess, "Popen", side_effect=AssertionError("process import")), \
     patch.object(socket, "socket", side_effect=AssertionError("network import")):
    _spec.loader.exec_module(_build)
    _phase_spec = importlib.util.spec_from_file_location("books_pack_phase_under_test", ROOT / "scripts/build_phase.py")
    _phase = importlib.util.module_from_spec(_phase_spec)
    _phase_spec.loader.exec_module(_phase)


def fixture():
    tools = {
        "electron": "electron/electron-v44.4.5-win32-x64.zip",
        "nsis": "nsis/Bin/makensis.exe", "nsisRoot": "nsis",
        "nsisResources": "nsis-resources", "seven": "seven/bin/7za.exe",
        "icons": "icons/icon-tool.js", "npm": "npm/bin/npm-cli.js",
    }
    facts = {"size": 7, "sha256": "a" * 64}
    packages = [
        {"path": "node_modules/pkg", "version": "1.0.0"},
        {"path": "node_modules/pkg/node_modules/child", "version": "2.0.0"},
    ]
    config = {
        "schema": "books-pack-inputs-v1", "seedDirectory": "build-cache/pack-inputs",
        "electronVersion": "44.4.5", "builderVersion": "26.15.3", "iconConverterVersion": "1.2.3",
        "packageLockSha256": "b" * 64, "tools": tools,
        "files": {tools[k]: dict(facts) for k in ("electron", "nsis", "seven", "icons", "npm")},
        "productionPackages": packages,
        "productionFiles": {item["path"] + "/package.json": dict(facts) for item in packages},
    }
    config["productionFiles"]["node_modules/pkg/index.js"] = dict(facts)
    lock = {"lockfileVersion": 3, "packages": {
        "": {"version": "0.24.2"}, "node_modules/pkg": {"version": "1.0.0"},
        "node_modules/pkg/node_modules/child": {"version": "2.0.0"},
        "node_modules/dev-tool": {"version": "3.0.0", "dev": True},
    }}
    return config, lock


class AppPackageWriter:
    """Ordinary private-file stand-in for BuildTree.write, no native handles."""
    def __init__(self, root):
        self.root = root
        self.manifest = {}
        self.paths = []

    def write(self, target, chunks):
        if target != self.root / "package.json":
            raise AssertionError("unexpected stage output")
        content = b"".join(chunks)
        with target.open("xb") as output:
            output.write(content)
        facts = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
        self.paths.append(target)
        self.manifest["package.json"] = facts
        return facts


class PackInputTests(unittest.TestCase):
    def setUp(self):
        self.config, self.lock = fixture()
        self.native = self.enterContext(patch.object(ctypes, "WinDLL", side_effect=AssertionError("native API"), create=True))
        self.process = self.enterContext(patch.object(subprocess, "Popen", side_effect=AssertionError("child process")))
        self.network = self.enterContext(patch.object(socket, "socket", side_effect=AssertionError("network")))
        self.addCleanup(self._no_native_attempts)

    def _no_native_attempts(self):
        for mock in (self.native, self.process, self.network):
            mock.assert_not_called()

    def reject(self, config=None, lock=None):
        with self.assertRaises(RuntimeError):
            _build.validate_pack_inputs(self.config if config is None else config, self.lock if lock is None else lock)

    def test_valid_inventory_preserves_bytes_and_accepts_explicit_nested_package(self):
        before = copy.deepcopy((self.config, self.lock))
        self.assertIs(_build.validate_pack_inputs(self.config, self.lock), self.config)
        self.assertEqual((self.config, self.lock), before)
        self.assertIsNone(_build.K)

    def test_committed_inventory_matches_its_lock_and_complete_production_membership(self):
        config = _build.load_pack_inputs(ROOT)
        lock = json.loads((ROOT / "package-lock.json").read_text("utf8"))
        expected = {p for p, item in lock["packages"].items() if p and item.get("dev") is not True}
        self.assertEqual({p["path"] for p in config["productionPackages"]}, expected)
        self.assertTrue(all(p + "/package.json" in config["productionFiles"] for p in expected))

    def test_nonobject_config_and_lock_refuse_cleanly(self):
        for value in (None, [], "manifest", 7):
            with self.subTest(value=value, target="config"), self.assertRaises(RuntimeError):
                _build.validate_pack_inputs(value, self.lock)
            with self.subTest(value=value, target="lock"), self.assertRaises(RuntimeError):
                _build.validate_pack_inputs(self.config, value)

    def test_schema_lock_version_and_seed_directory_are_exact(self):
        for field, value in (("schema", "future"), ("seedDirectory", "../seed"), ("seedDirectory", "C:/seed")):
            changed = copy.deepcopy(self.config); changed[field] = value
            with self.subTest(field=field, value=value): self.reject(changed)
        for value in (None, 2, "3", True):
            changed = copy.deepcopy(self.lock); changed["lockfileVersion"] = value
            with self.subTest(lock_version=value): self.reject(lock=changed)

    def test_empty_or_wrong_file_map_refuses(self):
        for field in ("files", "productionFiles"):
            for value in ({}, [], None, "files"):
                changed = copy.deepcopy(self.config); changed[field] = value
                with self.subTest(field=field, value=value): self.reject(changed)

    def test_traversal_absolute_backslash_empty_segments_and_nul_refuse(self):
        for field in ("files", "productionFiles"):
            for name in ("../escape", "a/../escape", "/absolute", "C:/absolute", "a\\b", "a//b", "a/./b", "a/", "a\0b"):
                changed = copy.deepcopy(self.config); changed[field][name] = {"size": 1, "sha256": "a" * 64}
                with self.subTest(field=field, name=name): self.reject(changed)

    def test_case_colliding_file_names_refuse(self):
        for field in ("files", "productionFiles"):
            changed = copy.deepcopy(self.config); name = next(iter(changed[field]))
            changed[field][name.upper()] = copy.deepcopy(changed[field][name])
            with self.subTest(field=field): self.reject(changed)

    def test_file_fingerprints_require_exact_shape_integer_size_and_lowercase_sha(self):
        bad = [None, [], {}, {"size": 1}, {"sha256": "a" * 64},
               {"size": True, "sha256": "a" * 64}, {"size": -1, "sha256": "a" * 64},
               {"size": 1.5, "sha256": "a" * 64}, {"size": "1", "sha256": "a" * 64},
               {"size": 1, "sha256": "A" * 64}, {"size": 1, "sha256": "z" * 64},
               {"size": 1, "sha256": "a" * 63}, {"size": 1, "sha256": None},
               {"size": 1, "sha256": "a" * 64, "extra": True}]
        for field in ("files", "productionFiles"):
            for facts in bad:
                changed = copy.deepcopy(self.config); changed[field][next(iter(changed[field]))] = facts
                with self.subTest(field=field, facts=facts): self.reject(changed)
        self.config["files"]["empty-file"] = {"size": 0, "sha256": hashlib.sha256(b"").hexdigest()}
        self.assertIs(_build.validate_pack_inputs(self.config, self.lock), self.config)

    def test_production_membership_rejects_missing_extra_dev_duplicate_and_version_drift(self):
        variants = []
        changed = copy.deepcopy(self.config); changed["productionPackages"].pop(); variants.append(changed)
        for item in ({"path": "node_modules/extra", "version": "1.0.0"}, {"path": "node_modules/dev-tool", "version": "3.0.0"}, self.config["productionPackages"][0]):
            changed = copy.deepcopy(self.config); changed["productionPackages"].append(copy.deepcopy(item)); variants.append(changed)
        changed = copy.deepcopy(self.config); changed["productionPackages"][0]["version"] = "9.0.0"; variants.append(changed)
        for changed in variants:
            with self.subTest(packages=changed["productionPackages"]): self.reject(changed)

    def test_malformed_package_records_and_lock_members_refuse(self):
        for value in ([], None, "packages"):
            changed = copy.deepcopy(self.config); changed["productionPackages"] = value
            with self.subTest(packages=value): self.reject(changed)
        for item in (None, [], {}, {"path": "node_modules/pkg"}, {"path": "../pkg", "version": "1"}, {"path": "other/pkg", "version": "1"}, {"path": "node_modules/pkg", "version": "1", "extra": True}):
            changed = copy.deepcopy(self.config); changed["productionPackages"] = [item]
            with self.subTest(item=item): self.reject(changed)
        for value in (None, [], {"node_modules/pkg": None}, {"node_modules/pkg": {}}):
            changed = copy.deepcopy(self.lock); changed["packages"] = value
            with self.subTest(lock_packages=value): self.reject(lock=changed)

    def test_unapproved_nested_package_cannot_hide_under_approved_parent(self):
        self.config["productionFiles"]["node_modules/pkg/node_modules/rogue/index.js"] = {"size": 1, "sha256": "a" * 64}
        self.reject()

    def test_ownerless_production_file_refuses(self):
        self.config["productionFiles"]["node_modules/other/index.js"] = {"size": 1, "sha256": "a" * 64}
        self.reject()

    def test_every_approved_package_requires_its_own_package_json(self):
        for item in self.config["productionPackages"]:
            changed = copy.deepcopy(self.config); del changed["productionFiles"][item["path"] + "/package.json"]
            with self.subTest(package=item["path"]): self.reject(changed)

    def test_tool_mapping_missing_seed_and_version_changes_refuse(self):
        for name in self.config["tools"]:
            changed = copy.deepcopy(self.config); changed["tools"][name] = "other/tool"
            with self.subTest(tool=name): self.reject(changed)
        for name in ("electron", "nsis", "seven", "icons", "npm"):
            changed = copy.deepcopy(self.config); del changed["files"][changed["tools"][name]]
            with self.subTest(missing_seed=name): self.reject(changed)
        for name in ("electronVersion", "builderVersion", "iconConverterVersion"):
            changed = copy.deepcopy(self.config); changed[name] = "0.0.0"
            with self.subTest(version=name): self.reject(changed)

    def test_loader_binds_exact_lock_bytes_before_validation(self):
        with tempfile.TemporaryDirectory(prefix="books-pack-inputs-") as folder:
            root = Path(folder); (root / "scripts").mkdir()
            lock = json.dumps(self.lock, sort_keys=True).encode()
            self.config["packageLockSha256"] = hashlib.sha256(lock).hexdigest()
            manifest = json.dumps(self.config).encode()
            (root / "package-lock.json").write_bytes(lock)
            (root / "scripts/build-inputs.json").write_bytes(manifest)
            self.assertEqual(_build.load_pack_inputs(root), self.config)
            (root / "package-lock.json").write_bytes(lock + b"\n")
            with self.assertRaisesRegex(RuntimeError, "lockfile fingerprint"):
                _build.load_pack_inputs(root)
            self.assertEqual((root / "scripts/build-inputs.json").read_bytes(), manifest)
            self.assertEqual((root / "package-lock.json").read_bytes(), lock + b"\n")


    def test_loader_rejects_duplicate_json_keys_even_with_matching_lock_hash(self):
        for target in ("manifest", "lock"):
            with self.subTest(target=target), tempfile.TemporaryDirectory(prefix="books-pack-duplicates-") as folder:
                root = Path(folder); (root / "scripts").mkdir()
                config, lock = fixture()
                lock_text = json.dumps(lock)
                if target == "lock":
                    lock_text = lock_text.replace('"lockfileVersion": 3', '"lockfileVersion": 2, "lockfileVersion": 3', 1)
                lock_bytes = lock_text.encode()
                config["packageLockSha256"] = hashlib.sha256(lock_bytes).hexdigest()
                manifest = json.dumps(config)
                if target == "manifest":
                    manifest = manifest.replace('"schema": "books-pack-inputs-v1"', '"schema": "bad", "schema": "books-pack-inputs-v1"', 1)
                (root / "package-lock.json").write_bytes(lock_bytes)
                (root / "scripts/build-inputs.json").write_text(manifest, encoding="utf8")
                with self.assertRaisesRegex(RuntimeError, "[Dd]uplicate"):
                    _build.load_pack_inputs(root)
                self.assertEqual((root / "package-lock.json").read_bytes(), lock_bytes)
                self.assertEqual((root / "scripts/build-inputs.json").read_text("utf8"), manifest)

    def test_staged_application_package_keeps_real_runtime_identity_and_dependencies(self):
        project_bytes = (ROOT / "package.json").read_bytes()
        project = json.loads(project_bytes)
        with tempfile.TemporaryDirectory(prefix="books-app-package-") as folder:
            stage = Path(folder)
            writer = AppPackageWriter(stage)
            facts = _phase.stage_app_package(writer, stage, project)
            app = json.loads((stage / "package.json").read_bytes())
            self.assertEqual(app, {"name": "books-arranger", "productName": "Books Arranger",
                "version": "0.24.2", "private": True,
                "description": project["description"], "main": "desktop/main.js",
                "dependencies": {"electron-updater": "6.8.9"}})
            self.assertEqual(facts, writer.manifest["package.json"])
            pins = json.loads((ROOT / "scripts/build-inputs.json").read_bytes())
            self.assertEqual(len(pins["productionPackages"]), 16)
            self.assertEqual(len(pins["productionFiles"]), 319)
            self.assertEqual(app["dependencies"], project["dependencies"])
        self.assertEqual((ROOT / "package.json").read_bytes(), project_bytes)

    def test_staged_package_removes_only_project_tooling_without_mutating_project(self):
        project = {"name": "fixture-app", "version": "1.2.3", "main": "desktop/main.js",
            "dependencies": {"runtime": "1.0.0"}, "optionalDependencies": {"optional": "2.0.0"},
            "type": "commonjs", "exports": {".": "./desktop/main.js"}, "engines": {"node": ">=22"},
            "description": "Unicode é metadata", "license": "MIT", "customRuntime": {"nested": [1, True]},
            "build": {"appId": "fixture.id", "publish": {"provider": "github"}},
            "devDependencies": {"electron": "44.4.5"}, "scripts": {"postinstall": "must not run"},
            "allowScripts": {"tool": False}, "directories": {"output": "dist"}}
        before = copy.deepcopy(project)
        with tempfile.TemporaryDirectory(prefix="books-app-package-") as folder:
            stage = Path(folder)
            _phase.stage_app_package(AppPackageWriter(stage), stage, project)
            app = json.loads((stage / "package.json").read_bytes())
            for name in ("build", "devDependencies", "scripts", "allowScripts", "directories"):
                self.assertNotIn(name, app)
            for name in ("name", "version", "main", "dependencies", "optionalDependencies", "type", "exports", "engines", "description", "license", "customRuntime"):
                self.assertEqual(app[name], before[name])
        self.assertEqual(project, before)

    def test_staged_package_manifest_binds_generated_bytes_instead_of_project_copy(self):
        project = json.loads((ROOT / "package.json").read_bytes())
        with tempfile.TemporaryDirectory(prefix="books-app-package-") as folder:
            stage = Path(folder)
            writer = AppPackageWriter(stage)
            _phase.stage_app_package(writer, stage, project)
            content = (stage / "package.json").read_bytes()
            self.assertEqual(writer.paths, [stage / "package.json"])
            self.assertEqual(writer.manifest, {"package.json": {
                "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}})
            self.assertNotEqual(content, (ROOT / "package.json").read_bytes())
            self.assertNotEqual(writer.manifest["package.json"]["sha256"],
                hashlib.sha256(content.replace(b'0.24.2', b'0.24.3')).hexdigest())


if __name__ == "__main__":
    unittest.main()
