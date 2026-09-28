# Loader smoke module

This public fork adds an independently written GPL-2.0-only test module to
the public Ylarod DDK. It includes no device dumps, existing driver binaries,
or code from private repositories.

**Scope: this public repository is only a Workflow compilation workspace.**
Loader implementation, device experiments and their results stay in separate
local workspaces. No device-side execution is performed by this repository.

## Build

Run **Build loader smoke module** in GitHub Actions. The workflow uses the
public `android13-5.15` DDK image pinned by digest, with its original Kbuild
configuration and compiler. The module is not binary-patched, stripped of
versions, or built with overridden CFI/signature/force-load settings.

Artifacts include the `.ko`, generated `.mod.c`, compiler identity, kernel
configuration, image metadata, ELF/relocation listing, disassembly, module
SHA-256, and `audit.json`. The audit requires nonempty symbol versions,
`module_layout`, version coverage for strong imports, and init/exit entries.
`device_load_test` stays `not_run`; compilation is not a device-load result.

## Behavior

- Initialization logs one message and sets `ready=true`.
- Read-only sysfs module parameters expose `cookie`, `ready`, and `fail_init`.
- `cookie` verifies that a loader forwards an unsigned integer parameter.
- `fail_init=true` returns `-EINVAL` before allocating resources.
- Unload clears the module's own state and logs one message.
- There are no hooks, work queues, processes, external memory accesses, or
  persistent device configuration changes.

## Device test acceptance

On a compatible test kernel, compare normal loading and the loader under
test: parameter delivery, readiness, normal unload, expected initialization
failure, and repeat load/unload. Keep the original artifact unchanged and
record kernel build identity alongside the result. Do not run the module
automatically from CI; this workflow only compiles and inspects it.

The first target is ARM64 android13-5.15. Additional targets should be added
with their own image digests and retained build/audit evidence.
