# AOS 3.6 — Signed GitHub Release Updates (Experimental)

Repository: https://github.com/bravo-nineteen/airsoft-os

## Security model
GitHub is an untrusted transport; update ZIPs are only accepted after Ed25519
signature and SHA-256 verification. No release key is bundled. Generate your own
private key offline and copy only the public key to each AOS computer. Publishing
a new GitHub Release alone CANNOT update computers without a matching signature.

The updater never executes postinstall scripts and accepts only allowlisted
application files. It does not update system services, dependency packages or its
own privileged update agent. Reinstall manually for system integration changes.

## First-time setup (on your personal trusted Linux computer)

    openssl genpkey -algorithm Ed25519 -out aos-signing-private.pem
    openssl pkey -in aos-signing-private.pem -pubout -out aos-signing-public.pem

Keep aos-signing-private.pem private, never in your public GitHub repo or a public
CI Actions secret. Upload ONLY the public PEM to the repository if desired.

On the Toughbook after installing this release:

    sudo install -d -m 755 /etc/aos
    sudo install -m 644 aos-signing-public.pem /etc/aos/trusted-release-key.pem
    /opt/aos/.venv/bin/python /opt/aos/aos_github.py configure bravo-nineteen/airsoft-os /etc/aos/trusted-release-key.pem

To build a release package on your trusted workstation:

    python3 release_tools/build_release.py . ./release-assets --signing-key /secure/path/aos-signing-private.pem

Create a GitHub Release with tag `v3.6.0`, upload exactly these assets:
`aos-update.zip`, `aos-manifest.json`, `aos-manifest.sig`.

On the Toughbook:

    /opt/aos/.venv/bin/python /opt/aos/aos_github.py check
    /opt/aos/.venv/bin/python /opt/aos/aos_github.py download
    sudo /opt/aos/.venv/bin/python /opt/aos/aos_apply_update.py install ~/Downloads/AOS-Updates/AOS-3.6.0

Replace 3.6.0 with the actual release version. The installer prints a rollback
command and requires a full AOS session restart. If the user is not in sudoers,
run the install command from an administrator account.

## Limitations
- Does not self-update installer scripts, privileged updater, or Debian packages.
- Application files are replaced individually; sudden power loss is not atomic.
- Backups can be manually restored; there is no automatic health-check rollback.
- Release installation is administrator-approved and not silent/unattended.
- No CF-19 hardware validation yet. Keep the ordinary Debian session available.
