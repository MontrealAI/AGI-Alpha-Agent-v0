# Results-directory security correction

Current-rule inspection reproduced a real filesystem defect in the legacy Insight
simulation-results initializer. The previous mkdir(exist_ok=True) followed by
chmod followed a configured final-directory symlink and changed an unrelated
owned target from 0755 to 0700. The reproduction used those actual source AST
statements on owned inert temporary directories; no server or network was used.

The initializer now walks directories through no-follow POSIX handles, verifies
trusted ancestors and operator ownership, applies permissions to the opened
directory descriptor and detects final-path replacement. Configured output or
ancestor links refuse. A root-owned default system /tmp alias is canonicalized
before appending the owned application directories, preserving the standard
macOS alias. Unsupported handle platforms refuse explicitly. Windows private ACL
behavior is not qualified, and this compatibility boundary requires exact-source
review before release. No published Alpha1.42 file/profile/manifest is changed.

Ten focused actual-helper regressions pass from both the repository and /tmp.
They cover ordinary creation/reuse, final and ancestor links, swaps before/after
open, unprotected writable ancestors, the default system alias, files/root/parent
traversal and unsupported capabilities. This protects preparation/chmod; it does
not claim resistance to arbitrary hostile same-user mutation throughout later
result reads/writes. The existing routes, methods and result schema remain.

The [d7 current-rule review](security-current-rule-review-d7.json) separately binds
all57 historical d7 findings to exact current DE5 source/rule definitions. All five
rule spans match the actual captured policy. E3 missing definitions are not a
dependency for that DE5 scan. Those are operator-authored source/semantics notes,
not eligible Security dispositions; all owner decisions remain UNKNOWN. This
changed source needs its own complete official scan and review. No exception map,
scanner suppression, reduced coverage or security-policy change is introduced.

The hosted78da source browser mission passed before the final lock fixture test
failed: the source ZIP has nine verified members,6702bytes and SHA256
8f6ff8ff3edf4f0d46cda02178ea4dc36eb4ddb63dce1d3863653dec47778c2a.
The signed export was independently verified. This was one isolated CI mission,
not approved-operator acceptance, a customer order or measured commercial value.
The lock test's relative wheelhouse fixture now uses the actual working directory;
all70 cases pass from both source root and /tmp with unchanged product criteria.

## Français

La correction empêche qu'un lien de répertoire redirige le changement de
permissions vers une autre cible. Les dix essais ciblés réussissent; le traitement
du répertoire temporaire système standard de macOS est conservé. Les plateformes
sans les garanties nécessaires refusent explicitement cette initialisation.
La qualification des ACL Windows, la validation finale de sécurité et
l'acceptation dans l'installation de l'opérateur restent distinctes.
