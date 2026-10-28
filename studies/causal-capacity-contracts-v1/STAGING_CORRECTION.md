# Staging identity correction (preserved failure)

First upload attempted to stage the 200,904-byte manifest PDF but inadvertently took bytes from a mutable working-output path that had been overwritten by a different 264,314-byte PDF. The initial Git tree stored blob SHA-1 `b2f3f7d21b87053e4834414bfbbf524ea2afa91d` (264,314 bytes), not the manifest-matching original. That mismatch was detected by inspecting the Git tree *after* opening the draft review PR.

The corrected source was read **directly from the already verified original archive extraction**, not the working output path. It has SHA-256 `6f26d4c82da4125924614997247638c28348a6669dce4456767b250fda92a1a0`, length 200,904 bytes and Git blob SHA-1 `a6e980592305f7cee794364aa81d168bcbd7c223`. Its upload was performed through a separately identified base64 transfer and Git returned exactly that SHA-1.

This correction commit changes only the staged PDF and adds this record. It does **not** qualify publication, source-catalog integration, release artifacts or the live site. Historical failure remains in the branch history and must not be relabeled as a passing source.
