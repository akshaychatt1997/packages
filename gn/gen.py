#!/usr/bin/env python
# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import gn
import os
import paths
import subprocess
import sys


class Amalgamation:
    def __init__(self):
        self.labels = []
        self.binaries = []

    def add_config(self, config):
        if config.get("label"):
            self.labels.append(config["label"])
        for b in config.get("binaries", []):
            binary = {}
            binary["binary"] = b["binary"]
            binary["bootfs_path"] = b["bootfs_path"]
            self.binaries.append(binary)

def resolve_imports(import_queue):
    imported = set(import_queue)
    amalgamation = Amalgamation()
    while import_queue:
        config_name = import_queue.pop()
        config_path = os.path.join(paths.SCRIPT_DIR, config_name)
        with open(config_path) as f:
            try:
                config = json.load(f)
                amalgamation.add_config(config)
                for i in config.get("imports", []):
                    if i not in imported:
                        import_queue.append(i)
                        imported.add(i)
            except Exception as e:
                print "Failed to parse config %s, error %s" % (config_path, str(e))
    return amalgamation

def main():
    parser = argparse.ArgumentParser(description="Generate Ninja files for Fuchsia")
    parser.add_argument("--modules", "-m", help="comma separted list of modules",
                        default="default")
    parser.add_argument("--outdir", "-o", help="output directory", default="out/Debug")
    args = parser.parse_args()

    amalgamation = resolve_imports(args.modules.split(","))

    with open(os.path.join(paths.SCRIPT_DIR, "BUILD.gn"), "w") as build_gn:
        build_gn.write("""
# NOTE: This file is auto-generated by gen.py. Do not edit by hand.

group("default") {
  testonly = true
  deps = [
    "//packages/gn/mkbootfs",
""")
        for label in amalgamation.labels:
            build_gn.write("""
    "%s",""" % label)
        build_gn.write("""
  ]
}
""")
    outdir_path = os.path.join(paths.FUCHSIA_ROOT, args.outdir)
    pkg_gen_dir = os.path.join(outdir_path, "gen", "packages", "gn", "mkbootfs")
    if not os.path.isdir(pkg_gen_dir):
        os.makedirs(pkg_gen_dir)
    with open(os.path.join(pkg_gen_dir, "user.bootfs.manifest"), "w") as manifest:
        for binary in amalgamation.binaries:
            binary_path = os.path.join(outdir_path, binary["binary"])
            manifest.write("""%s=%s
""" % (binary["bootfs_path"], binary_path))
    with open(os.path.join(pkg_gen_dir, "user.bootfs.d"), "w") as depfile:
        depfile.write("user.bootfs: gen/packages/gn/mkbootfs/user.bootfs.manifest")
        for binary in amalgamation.binaries:
            depfile.write(" %s" % binary["binary"])
        depfile.write("\n")
    dotfile_path = os.path.join(paths.SCRIPT_DIR, ".gn")

    return gn.run(["gen", outdir_path, "--check"])


if __name__ == "__main__":
    sys.exit(main())
