# Landfall — script dei videotutorial

Testo da leggere, un paragrafo per ogni schermata; il tempo a sinistra è quello in cui la schermata compare nel video.

## 01 Installazione

- `00:00:00` **Installare Landfall** — Download dello zip e installazione in Blender 5.2
- `00:00:03` Landfall vive su GitHub: github.com/lucafrancescoorlandi/landfall. Il README è la documentazione completa; le guide PDF sono nella cartella docs.
- `00:00:08` A destra, sotto Releases, apri l'ultima versione: sotto Assets scarica landfall-x.x.x.zip. Non decomprimerlo: Blender vuole lo zip così com'è.
- `00:00:14` In Blender apri Edit › Preferences e scegli la scheda Add-ons.
- `00:00:19` La freccia in alto a destra apre un menu: scegli Install from Disk… e seleziona lo zip appena scaricato.
- `00:00:25` Landfall compare nell'elenco. Controlla che la casella sia spuntata e che il numero di versione sia quello del file.
- `00:00:30` Aprendo la freccia accanto al nome vedi le preferenze: sono già tutte accese. Landfall acceso è Maya; spento o disinstallato è Blender di fabbrica.
- `00:00:36` Chiudi le preferenze: il viewport ha già i colori di Maya, la griglia finita e la navigazione con Alt e il mouse.
- `00:00:41` Da una scena vuota premi Setup › Save as startup: preferenze e layout tornano uguali a ogni avvio.
- `00:00:46` **Fatto** — Le guide PDF sono nella cartella docs del repository

## 02 Aggiornamento

- `00:00:00` **Aggiornare Landfall** — Prima si disinstalla la versione vecchia, poi si installa la nuova
- `00:00:03` Installare uno zip nuovo sopra uno vecchio non è affidabile: Blender può continuare a eseguire il codice precedente mostrando il numero nuovo.
- `00:00:08` Quindi: Preferences › Get Extensions, cerca landfall.
- `00:00:14` Dalla freccia accanto all'estensione scegli Uninstall. Tema, griglia e navigazione tornano da soli a quelli di Blender.
- `00:00:19` Chiudi Blender e riaprilo: così nessuna copia compilata del vecchio codice resta in memoria.
- `00:00:25` Poi Preferences › Add-ons › Install from Disk… con lo zip nuovo, come alla prima installazione.
- `00:00:30` Controlla il numero di versione nelle preferenze: deve essere quello dello zip. Il set-up Maya torna acceso da solo.
- `00:00:36` Setup › Self check verifica menu, scorciatoie e keymap; due NOTE su Alt+Q e Alt+W sono normali.
- `00:00:41` **Fatto** — Le novità di ogni versione sono nel CHANGELOG

## 03 Il pannello a sinistra

- `00:00:00` **Il pannello a sinistra** — Dove si trova Landfall e come metterlo dove sta la shelf di Maya
- `00:00:03` Landfall compare in due posti. Il primo è la barra laterale del viewport: tasto N, linguetta Landfall.
- `00:00:08` Il secondo è l'editor Properties, scheda Scene. Stessi comandi. Blender non ammette pannelli nella barra degli strumenti a sinistra, quindi si apre un Properties sul lato sinistro.
- `00:00:14` Passo 1: nel viewport, View › Area › Vertical Split. Porta la linea vicino al bordo sinistro e fai click.
- `00:00:19` Passo 2: nell'area stretta appena creata, il pulsante in alto a sinistra sceglie il tipo di editor: Properties.
- `00:00:25` Passo 3: nella colonna di icone scegli Scene, quella con il cono e la sfera, e apri il pannello Landfall.
- `00:00:30` Chiudi i pannelli di Blender che non ti servono: Blender ricorda cosa lasci aperto.
- `00:00:36` In cima c'è il promemoria: G sposta, R ruota, S scala. Si spegne dalle preferenze quando non serve più.
- `00:00:41` Passo 4: da una scena vuota, Setup › Save as startup. Il layout torna così a ogni apertura.
- `00:00:46` **Fatto**

## 04 Tab Gizmos

- `00:00:00` **Gizmos** — Manipolatori, orientamento e pivot
- `00:00:03` La sezione Gizmos: l'interruttore generale, i tre manipolatori, il pulsante G R S e i due menu di orientamento e pivot.
- `00:00:08` Move, Rotate e Scale scelgono quali manipolatori vedere. Con la preferenza 'Same transform gizmos in every workspace' la scelta vale in tutti i workspace, come in Maya.
- `00:00:14` Premendo G resta acceso solo il manipolatore di spostamento…
- `00:00:19` …R quello di rotazione…
- `00:00:25` …S quello di scala. Come W, E, R in Maya. I tre pulsanti del pannello seguono.
- `00:00:30` Il pulsante 'G R S: gizmo only, like Maya', acceso di default: il tasto mostra solo il manipolatore e trasformi con le sue maniglie, che restano visibili.
- `00:00:36` Spento, il tasto avvia anche la trasformazione modale di Blender: assi X Y Z, numeri, Invio. Durante la modale Blender nasconde i gizmi.
- `00:00:41` Sotto: orientamento (Global, Local, Normal…) e pivot (Median Point, 3D Cursor…). I tasti virgola e punto aprono i loro pie.
- `00:00:46` Alt+W nasconde e mostra i manipolatori senza toccare il pannello; il gizmo di navigazione nell'angolo resta.
- `00:00:52` **Gizmos** — Nelle preferenze: Same transform gizmos · G, R and S pick the gizmo

## 05 Tab Display

- `00:00:00` **Display** — X-ray, wire, nascondi e mostra, isolate, border edges, colore
- `00:00:03` La sezione Display raccoglie quello che in Maya sta nel menu Display e nella shelf.
- `00:00:08` X-ray rende trasparenti solo gli oggetti selezionati; il cursore accanto regola l'opacità.
- `00:00:14` Wire on shaded: il wireframe sopra lo shading solido, come Wireframe on Shaded di Maya.
- `00:00:19` Hide nasconde la selezione. Show sel mostra gli oggetti nascosti selezionati nell'Outliner, Show last l'ultimo gruppo nascosto, Show all tutto.
- `00:00:25` In Edit Mode gli stessi pulsanti lavorano sui componenti: nascondono e mostrano le facce.
- `00:00:30` Isolate è la Local View di Blender: solo la selezione. Di nuovo per tornare. In Edit Mode nasconde il resto della mesh.
- `00:00:36` Border edges disegna in arancione gli spigoli aperti: bordi e buchi della mesh. Sotto, spessore e colore; Select border edges li seleziona in Edit Mode.
- `00:00:41` Object color: otto colori e uno libero per gli oggetti selezionati, la X torna al bianco. Mette lo shading del viewport su Object.
- `00:00:46` **Display**

## 06 Tab Modeling

- `00:00:00` **Modeling** — Pivot, freeze, estrusione di Maya, merge, smooth preview
- `00:00:03` La sezione Modeling. In Object Mode i comandi di Edit Mode sono grigi; qui siamo in Edit Mode con una faccia selezionata.
- `00:00:08` Center pivot porta l'origine al centro della geometria. Edit pivot: tieni premuto, poi G ed R spostano l'origine invece dell'oggetto; ripremi per uscire.
- `00:00:14` Freeze applica posizione, rotazione e scala, come Freeze Transformations. Hierarchy seleziona i figli; Inverse inverte la selezione.
- `00:00:19` Extrude with options è il polyExtrudeFace di Maya: thickness, offset, divisions, keep faces together, twist e taper. È anche sul tasto E.
- `00:00:25` Premi E, muovi il mouse, conferma: il pannello in basso a sinistra mostra i sei parametri e lo spostamento, modificabili finché l'estrusione è l'ultima operazione.
- `00:00:30` Thickness 0 tiene la distanza del mouse; un altro valore la sostituisce. Con soli spigoli o vertici selezionati, E passa all'estrusione di Blender.
- `00:00:36` Merge by distance unisce i vertici entro una soglia; Merge at center li fonde in un punto. Spin ruota lo spigolo, Detach separa le facce, Grid fill riempie un anello chiuso.
- `00:00:41` Smooth preview: Alt+1 mostra solo la gabbia…
- `00:00:46` …Alt+2 la superficie liscia con la gabbia sopra…
- `00:00:52` …Alt+3 solo la superficie. È il Subdivision Surface di Blender, quindi resta nello stack: Subdivisions regola il livello, Apply smooth lo applica per sempre.
- `00:00:57` **Modeling**

## 07 Tab Texturing

- `00:00:00` **Texturing** — UV e set PBR
- `00:00:03` La sezione Texturing, in Edit Mode.
- `00:00:08` Unwrap + scale + pack fa in un passo quello che in Maya sono tre comandi: unwrap, scala media delle isole, pack.
- `00:00:14` Pla, Cyl, Sph, Auto: le proiezioni planare, cilindrica, sferica e automatica.
- `00:00:19` Load PBR set: scegli le immagini di un set e Landfall costruisce il Principled BSDF collegando ogni mappa dal nome: basecolor, roughness, metallic, normal, height, emission, opacity…
- `00:00:25` Reload textures ricarica dal disco tutte le immagini del file, dopo averle ridipinte fuori.
- `00:00:30` **Texturing**

## 08 Tab Editors and output

- `00:00:00` **Editors and output** — Workspace, playblast, quad view, regioni
- `00:00:03` La sezione Editors and output.
- `00:00:08` UV e Shading passano ai workspace UV Editing e Shading di Blender, come le finestre UV Editor e Hypershade di Maya.
- `00:00:14` Playblast: il render OpenGL dell'animazione dal viewport, come in Maya. Il risultato segue le impostazioni di output del render.
- `00:00:19` Quad view, o Ctrl+Alt+Q: quattro viste nel viewport, alto, fronte, lato e prospettiva. Di nuovo per tornare.
- `00:00:25` Toolbar, Sidebar e Header mostrano o nascondono quelle regioni in tutti i viewport insieme.
- `00:00:30` **Editors and output**

## 09 Tab Project

- `00:00:00` **Project** — La sezione del pannello
- `00:00:03` La sezione Project. In alto il nome del progetto attivo, o 'No project set'.
- `00:00:08` Create crea le cartelle di un nuovo progetto e lo imposta; Set imposta come attiva una cartella di progetto esistente.
- `00:00:14` Open scene e Save as lavorano dentro scenes/: sono anche Ctrl+O e Ctrl+Shift+S. Ctrl+S resta quello di Blender.
- `00:00:19` Make paths relative rende relativi tutti i percorsi esterni, da fare prima di spostare il progetto. Write workspace.mel scrive il file di progetto di Maya.
- `00:00:25` **Project** — Il video 13 mostra il flusso completo

## 10 Tab Setup

- `00:00:00` **Setup** — Il set-up Maya in un colpo solo
- `00:00:03` La sezione Setup, in fondo al pannello: accende e spegne insieme le cinque impostazioni in stile Maya. La riga sopra dice quante sono attive.
- `00:00:08` Turn on accende navigazione, marking menu, wire contestuale, colori e griglia. Turn off le spegne: serve a lavorare alla Blender tenendo l'add-on installato.
- `00:00:14` Save as startup salva preferenze e file di avvio: layout e impostazioni tornano a ogni apertura.
- `00:00:19` Self check verifica menu, scorciatoie e keymap e scrive il risultato nel text block landfall_self_check.
- `00:00:25` Navigation e Marking menu sono gli stessi interruttori delle preferenze, a portata di mano.
- `00:00:30` Maya colors applica il tema di Maya; la freccia rimette il tema precedente, l'altra icona quello di fabbrica.
- `00:00:36` Finite grid: una griglia che finisce, come quella di Maya: 22 celle di 1 metro per lato, regolabili accanto. Follow theme le dà il colore del tema.
- `00:00:41` Spenta, torna il pavimento infinito di Blender, con le sue linee degli assi. Da vicino i due si somigliano; la differenza si vede allontanando la vista.
- `00:00:46` Shortcuts apre la scheda con tutte le scorciatoie: resta sopra il viewport, si sposta trascinandola e legge i tasti dal keymap.
- `00:00:52` **Setup** — Landfall acceso è Maya, spento è Blender

## 11 Scorciatoie e marking menu

- `00:00:00` **Scorciatoie e marking menu** — Ctrl+Tab, Shift+Q, Alt+Q, E, F, Shift+F
- `00:00:03` Ctrl+Tab apre il marking menu, al posto del pie delle modalità di Blender. In Object Mode: le modalità a sinistra, Edit e Sculpt a destra, Display ed Edit sopra.
- `00:00:08` Un click su un ramo apre il suo elenco, ancorato sotto la voce. Le voci non mostrano tasti, come in Maya.
- `00:00:14` In Edit Mode: vertice, spigolo e faccia a sinistra, come i tasti 1, 2, 3; Modeling a destra con i comandi di modellazione.
- `00:00:19` Il ramo Modeling: i comandi di modellazione in due colonne, Make face compreso.
- `00:00:25` Shift+Q: il pie di Landfall con gli otto comandi più usati, in ogni modalità.
- `00:00:30` Shift+Alt+Q: il pie di modellazione in Edit Mode. Shift+Alt+X: lo snap pie, come la X di Maya.
- `00:00:36` Alt+Q: la hotbox, tutte le sezioni del pannello in colonne sotto il mouse.
- `00:00:41` E estrude con i parametri di Maya. F inquadra la selezione, anche in Edit Mode. Shift+F crea la faccia (Make Edge/Face di Blender).
- `00:00:46` G, R, S mostrano il manipolatore corrispondente. Alt+1 2 3 lo smooth preview, Alt+W i gizmi, Backspace cancella come X e Canc.
- `00:00:52` La scheda Shortcuts le elenca tutte. Per cambiarne una: Preferences › Keymap, cerca landfall, e cambia ogni copia, una per modalità.
- `00:00:57` **Scorciatoie**

## 12 Navigazione Maya

- `00:00:00` **Navigazione Maya** — Alt + mouse, F, Home, doppio click
- `00:00:03` Con Navigation acceso, nel pannello Setup o nelle preferenze, il viewport si guida come in Maya.
- `00:00:08` Alt + tasto sinistro orbita attorno alla selezione…
- `00:00:14` …Alt + tasto centrale sposta, Alt + tasto destro avvicina e allontana verso il puntatore.
- `00:00:19` F inquadra la selezione, in Object Mode e in Edit Mode sui componenti. Home inquadra tutto: è la A di Maya (sul portatile Fn + freccia sinistra).
- `00:00:25` Doppio click seleziona un loop di spigoli, Ctrl + doppio click un ring: in Blender erano Alt+click, che ora serve a orbitare.
- `00:00:30` L'interruttore imposta anche Orbit Around Selection, Auto Depth e Zoom to Mouse Position. La navigazione di Blender con il tasto centrale continua a funzionare.
- `00:00:36` Spento, o con Landfall disinstallato, tutto torna alle preferenze di fabbrica di Blender.
- `00:00:41` **Navigazione Maya**

## 13 Progetto in stile Maya

- `00:00:00` **Progetto in stile Maya** — Create, Set, Open scene, Save as, workspace.mel
- `00:00:03` Il sistema di progetto ricalca il Set Project di Maya: una cartella con scenes, sourceimages, images e le altre, e un workspace.mel che Maya riconosce.
- `00:00:08` Create: scegli dove e come chiamarlo. Landfall crea le cartelle, scrive il workspace.mel e imposta il progetto come attivo.
- `00:00:14` Il nome del progetto attivo compare in cima alla sezione. Set imposta un progetto esistente, anche uno creato da Maya.
- `00:00:19` Open scene, o Ctrl+O, apre il browser direttamente dentro scenes/. Senza progetto è l'Open di Blender.
- `00:00:25` Save as, o Ctrl+Shift+S, salva in scenes/ con i percorsi relativi. Un file già nel progetto resta dov'è. Ctrl+S sovrascrive il file corrente, come in Blender.
- `00:00:30` Prima di spostare o copiare il progetto, Make paths relative. Write workspace.mel aggiunge il file di Maya a un progetto creato senza.
- `00:00:36` Nelle preferenze: la cartella radice dei progetti, il render in images/, la cartella assets/ come libreria di asset.
- `00:00:41` **Progetto**
