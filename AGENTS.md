# Repository scope

This public fork is only for GitHub Actions compilation of the independently
written smoke-test kernel module and inspection of its build artifacts.

- Keep changes limited to the workflow, test-module source, build/audit
  scripts, and their documentation.
- Do not copy or publish loader implementation, private repository content,
  existing third-party driver binaries, device dumps, credentials, or
  real-device logs/results.
- Do not access the user's private repositories or their local copies.
- Keep device experiments and loader changes in separately authorized local
  workspaces, not this public repository.
- Do not publish container images or enable inherited image-release or
  feature-publication workflows. Use only the smoke-module build workflow.
- Building a module is not evidence that it loads on a device.
