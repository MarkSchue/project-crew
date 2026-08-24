lass uns mal gemeinsam anfangen, unsere überlegungen in einen plan zu giessen, den ich später herunterladen kann (md-file) und an einen coing agenten übergebe. Bislang wissen wir folgendes:
1. Wir setzen drei repositories auf:
a. ein repository in dem die agenten leben mit private und public bereich sowie registry und skill registry, etc..
b. ein repository in dem ein project-template untergebracht ist. das dient als blueprint für projekte und beinhaltet templates (user stories, spocs, regulatorik, etc). das kann mit der zeit erweitert werden, ist aber immer projektunabhängig.
c. ein repository für das eigentliche projekt mit public und private space. anforderungen (user stories) und spocs sind immer öffentlich, sensible daten dann agenten spezifisch private
2. wir wollen vs code al umgebung nutzen, um immer vollen zugriff auf alle dateien zu haben und auch eine gute übersicht über die agenten.
3. vs code kann auch al mcp-server für tools dienen.
4. tools sollen im gleichen repository abgelegt werden wie agenten
5. agenten haben zugriff auf das repository und  können bspw. committen
6. in vscode können neue agenten auch während der projektlaufzet erstellt werden.
7. für spocs oder auch agenten können dediziert modelle (llms) definiert werden.
8. sämtliches wissen der agenten soll im okf-format abgelegt werden, incl. yaml, log.md, index.md etc.
9. das projektwissen soll weitestgehend auch in verzeigertem okf-format abgelegt werden. das hilt den agenten beim lesen
10. spocs werden auch im okf-format abgelegt.
11. wenn afgaben ausgeführt werden, muss immer eine log-datei mitgeschrieben werden (welche agenten waren beteiligt, welche entscheidungen, war ein mensch beteiligt, welche spoc wurde ausgeführt, welche eingaben wurden gemacht, was war der input?...)
12. später soll noch eine weboberfläche für die bessere benutzung eingeführt werden.
13. agenten sollen auch als tools genutzt werden können, das hängt von den geforderten capabilities ab, die in der spoc definiert sind.
14. die auswahl der agenten erfolgt capability basiert. agenten besitzen eine liste an capabilities. die spocs erhalten ebenfalls anforderungen in form von capabilities. ein matching-agent erkennt dann, an wen die spoc übergeben wird und welche weiteren agenten ggfls. notwendig sind. aus dem procedure text der spoc leitet der matching-agent ggfls noch weitere notwendige capabilities ab.

soweit erstmal, kannst du einen ersten initialen md-plan erstellen (zum download)