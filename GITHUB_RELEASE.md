# Publishing v3.9.0 to bravo-nineteen/airsoft-os

## Current status
The connected GitHub integration can read the repository but returned 403 for
repository writes. This release therefore needs to be pushed/published by an
account with permission or through GitHub CLI on your computer.

## 1. Push the source code
Unzip `AOS_3_9_Repository_Source.zip` and copy its contents to a clone of
https://github.com/bravo-nineteen/airsoft-os (do not copy private keys).

    git clone https://github.com/bravo-nineteen/airsoft-os.git
    cd airsoft-os
    # copy the source package contents into this directory
    git add .
    git commit -m "AOS v3.9.0: resizable tactical desktop widgets"
    git push origin main

## 2. Sign the update offline (do NOT publish your private key)
Create your signing key on a trusted Linux computer:

    openssl genpkey -algorithm Ed25519 -out ~/aos-signing-private.pem
    chmod 600 ~/aos-signing-private.pem
    openssl pkey -in ~/aos-signing-private.pem -pubout -out ~/aos-signing-public.pem

If AOS already has a trusted release key, use its matching original private key
instead of generating a replacement. Do not rotate an existing signing key without
an authorised transition, or already-installed devices will reject the update.

In a trusted environment with dependencies installed:

    python3 release_tools/build_release.py . release-v3.9.0 \
      --signing-key ~/aos-signing-private.pem

The output must contain aos-update.zip, aos-manifest.json and aos-manifest.sig.

## 3. Publish GitHub Release
Install GitHub CLI, authenticate with `gh auth login` and execute:

    gh release create v3.9.0 \
      release-v3.9.0/aos-update.zip \
      release-v3.9.0/aos-manifest.json \
      release-v3.9.0/aos-manifest.sig \
      --repo bravo-nineteen/airsoft-os \
      --title "AOS 3.9.0 - Resizable Widgets" \
      --notes-file RELEASE_NOTES.md \
      --draft

Review on https://github.com/bravo-nineteen/airsoft-os/releases , then publish.

## 4. Update the Toughbook
Copy the matching trusted public key to `/etc/aos/trusted-release-key.pem`
via secure local installation; do not overwrite an existing trusted key casually.
Configure the desktop update checker:

    /opt/aos/.venv/bin/python /opt/aos/aos_github.py configure \
      bravo-nineteen/airsoft-os /etc/aos/trusted-release-key.pem
    /opt/aos/.venv/bin/python /opt/aos/aos_github.py check
    /opt/aos/.venv/bin/python /opt/aos/aos_github.py download

After verifying the staged directory, an administrator can install it:

    sudo /opt/aos/.venv/bin/python /opt/aos/aos_apply_update.py install \
      /home/YOUR_USERNAME/Downloads/AOS-Updates/AOS-3.9.0

Restart the AOS login session. The command prints the rollback backup path.

Important: Starting from AOS 3.8.2, the current on-device updater must already
be present and correctly configured. The GitHub release cannot update Debian
system libraries or replace the privileged update installer itself.

## Alternative: sign the supplied prebuilt GitHub release assets

Extract `AOS_3_9_UNSIGNED_Release_Assets.zip` somewhere outside your source
checkout. Then, from the source checkout run:

    python3 release_tools/sign_assets.py /path/to/assets-folder \
      --signing-key ~/aos-signing-private.pem

Verify the signed assets with the same public key the Toughbook trusts:

    python3 aos_release.py \
      /path/to/assets-folder/aos-update.zip \
      /path/to/assets-folder/aos-manifest.json \
      /path/to/assets-folder/aos-manifest.sig \
      ~/aos-signing-public.pem

Finally, on GitHub go to Releases → Draft a new release, set tag `v3.9.0`
and attach the three signed assets. Or publish with `gh release create`.
