# Repair deadlines follow the changed calendar

Review finding 4372585048 identified a user-visible rejection of valid planning
input. A four-slot initial calendar changed to eight slots permits a repair
deadline of eight. The UI incorrectly compared that deadline with the original
four slots. The existing fixed executor correctly inherits the changed task.

The one-line UI correction uses each phase’s effective inherited calendar. It
also refuses a repair deadline beyond a shortened changed calendar. Four cases
in English and French pass through the existing component test’s actual Prepare
handler: extension, shortening, explicit same-horizon repair and refusal of a
repair that restores the old horizon. Valid cases prepare only; no case approves
or runs work. The [original failure](before.txt) is preserved. The existing
[component suite](component-result.json) now passes 22 control groups/eight new
calendar transitions with simulated API/DOM. These are not browser/executor jobs.

The same eight format checks were added to the existing installed Chromium
acceptance. They assert that the request count does not change. Local Chromium
was previously refused; no retry is performed here. Fresh hosted exact-source
browser/installation acceptance remains required and is pending at this snapshot.

Only the corresponding source hash is explicitly updated in the candidate
installation manifest. Every other field, closed method set, permission, runtime
identity and scientific/worker body is unchanged, and every payload hash matches.
This declares a candidate for review; it does not adopt a new operator profile or
inherit earlier qualification. Security scanning, Code Review and actual
operator acceptance remain distinct. All historical v1–v4 source-offering
records remain unchanged; the source runner/checker bodies and their 210 local
tests/353-check operating replication are unchanged from b745d3da.

La correction utilise le calendrier effectivement modifié pour vérifier
l’échéance de réparation. Les huit transitions de format en anglais/français
n’autorisent aucun travail. Les contrôles dans le navigateur installé restent à
exécuter sur le code final; aucune installation approuvée, sécurité, fusion,
publication ou amélioration autonome n’est présumée.
