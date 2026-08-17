# PastilaAcida Private Code Signing V1

This checkpoint adds a provider-independent, fail-closed Authenticode stage for internal Scout releases. It does not claim public CA trust or SmartScreen reputation.

The non-secret authority is `packaging/windows/signing-authority-v1.json`. Private signing selects exactly one certificate by thumbprint from `Cert:\CurrentUser\My`; subject-only or first-available selection is forbidden. The key is RSA-3072, non-exportable, and remains in the owner profile. No PFX is created.

Release order is: copy the governed unsigned frozen payload to an external signing work root; sign and verify `PastilaScout.exe` and `pastila-scout.exe`; inventory their final signed bytes; compile the installer with the Inno external SignTool hook and signed uninstaller enabled; verify the installer; then calculate final hashes and write the receipt. Required signing never falls back to unsigned output.

Private V1 has no timestamp service: `TIMESTAMP_STATUS: NOT_CONFIGURED_PRIVATE_V1`. Future public signing must configure an approved RFC 3161 provider without changing artifact selection, ordering, verification, or receipt fields.

The public certificate may be installed only on owner-controlled machines. Importing it into CurrentUser TrustedPublisher and CurrentUser Root provides private trust; it does not provide public trust. Never distribute a private key or PFX. Reversal commands, using the recorded thumbprint, are:

```powershell
Remove-Item -LiteralPath 'Cert:\CurrentUser\TrustedPublisher\604635DF3EB4CAF406D977987B1A6AA764D83612'
Remove-Item -LiteralPath 'Cert:\CurrentUser\Root\604635DF3EB4CAF406D977987B1A6AA764D83612'
Remove-Item -LiteralPath 'Cert:\CurrentUser\My\604635DF3EB4CAF406D977987B1A6AA764D83612'
```

Remove only after verifying the exact thumbprint. The Personal-store command destroys the signing key and is intentionally last.

Rotation creates a finite-lifetime replacement identity, exports only its public certificate, updates the public certificate and thumbprint authority together, and repeats signing/tamper validation. Commercial migration replaces the certificate/provider configuration with a public CA or managed signer while retaining SignTool-compatible invocation and all pipeline gates.
