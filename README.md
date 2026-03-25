# Ring-LWE PoC : Introduction à la Cryptographie Post-Quantique

Alors tout d'abord, mettons les choses au clair : je ne suis pas expert en algorithmique post-quantique, ni dans le domaine quantique en général (que ce soit en physique ou en informatique). Je vous partage juste ici une petite implémentation que j'ai voulu mener afin de mieux comprendre les enjeux et le fonctionnement de ces algos pouvant faire face à des ordinateurs quantiques.

## 1) Comment lire le code

Pour les petits curieux qui n'ont pas forcément les connaissances de la librairie NumPy et/ou de Python, je vous ai mis deux types d'annotations dans le code :

* **Les Docstrings (`""" ... """`) :** présentes pour chaque fonction afin de comprendre ce qu'elle fait, comment et pourquoi.
* **Les commentaires classiques (`#`) :** pour les personnes encore moins à l'aise, j'ai laissé quelques commentaires pour vous expliquer le fonctionnement de chaque fonction NumPy, ainsi qu'un petit exemple.

Il suffit juste de faire fonctionner votre cerveau comme un compilateur maintenant !

## 2) Place au cours de maths

*(Il faut bien rentabiliser mes 12-14h hebdo !)*

C'est juste des éléments de cours sur des notions de base afin de comprendre la logique derrière le code :

### 1. Les Polynômes

Ce que c'est concrètement : un polynôme, c'est simplement une liste de nombres (ses coefficients) que l'on va stocker et manipuler. Par exemple, la suite (1, 2, 3, 4) donne le polynôme $1 + 2X + 3X^2 + 4X^3$, et ainsi de suite si notre liste est plus grande. Mathématiquement, la formule générale d'un polynôme de degré $n$ s'écrit avec la somme formelle suivante :

$$P(X) = \sum_{k=0}^{n} a_k X^k$$

où les $a_k$ représentent nos coefficients.

### 2. Le Modulo

En mathématiques, la congruence modulo $n$ (notée $a \equiv b \pmod n$) est une relation d'équivalence sur l'ensemble des entiers $\mathbb{Z}$. Formellement, on dit que deux entiers $a$ et $b$ sont congrus modulo $n$ s'ils ont le même reste dans la division euclidienne par $n$.

Concrètement, cela veut dire qu'il existe un entier relatif $k$ tel que :

$$a = k \times n + b$$

Si on passe le $b$ de l'autre côté de l'égalité, on retombe sur la définition algébrique stricte (leur différence est un multiple exact de $n$) :

$$a - b = k \times n$$

Dans la pratique, cela revient à travailler dans l'ensemble quotient $\mathbb{Z}/n\mathbb{Z}$ (souvent noté $\mathbb{Z}_n$). Au lieu de manipuler une infinité d'entiers, on ne conserve que les classes d'équivalence correspondant aux restes de la division euclidienne par $n$ (soit les entiers de $0$ à $n-1$). C'est ce qui empêche nos valeurs cryptographiques de saturer la mémoire.

### 3. Un Anneau

Un anneau est une structure algébrique fondamentale. Formellement, un anneau $(A, +, \times)$ est un ensemble muni de **deux** lois de composition interne qui vérifient les axiomes suivants :

1. $(A, +)$ est un **groupe commutatif** : l'addition est associative, l'ordre n'a pas d'importance (commutativité), il y a un élément neutre (le $0$), et chaque élément admet un opposé.
2. **Associativité de la multiplication** : quand on enchaîne des multiplications, l'ordre des calculs ne change rien ($(a \times b) \times c = a \times (b \times c)$).
3. **Élément neutre pour la multiplication** : il existe un élément (souvent noté $1$ ou $1_A$) qui ne modifie pas le résultat quand on multiplie par lui.
4. **La distributivité** : c'est la règle qui fait le pont entre nos deux lois. La multiplication $\times$ est distributive par rapport à l'addition $+$ (à gauche comme à droite, par exemple $a \times (b + c) = a \times b + a \times c$).

L'ensemble des polynômes à coefficients entiers, noté $\mathbb{Z}[X]$, forme un anneau.

### 4. L'Anneau Quotient $R_q = \mathbb{Z}_q[X]/(X^n+1)$

Bon, maintenant qu'on a les briques, on construit la maison.

Dans ce projet on travaille dans un anneau qui combine *tout ce qu'on vient de voir* : des polynômes, dont les coefficients sont modulo $q$, **et** dont le degré est borné. Cet objet s'appelle un **anneau quotient** et se note :

$$R_q = \mathbb{Z}_q[X] \;/\; (X^n + 1)$$

La barre oblique se lit comme un "modulo" mais pour les polynômes. On dit qu'on travaille "modulo le polynôme $X^n + 1$", ce qui impose la règle fondamentale :

$$X^n \equiv -1$$

Concrètement, dès qu'on obtient un terme de degré $\geq n$ après une multiplication, on le réduit en appliquant cette règle. Par exemple avec $n = 256$, si on obtient le terme $5 \cdot X^{260}$ :

$$5 \cdot X^{260} = 5 \cdot X^4 \cdot \underbrace{X^{256}}_{\equiv\; -1} \equiv -5 \cdot X^4$$

Ce terme vient donc **soustraire** 5 au coefficient de $X^4$. C'est exactement ce que fait le code dans `__mul__` :
```python
for i, c in enumerate(product):
    if i < self.n:
        result[i] += c          # degré OK, on garde
    else:
        result[i - self.n] -= c # X^(n+k) → -X^k  (car X^n = -1)
```

Pourquoi $-1$ et pas $0$ ? Si on choisissait $X^n \equiv 0$, certains polynômes non-nuls auraient un produit nul (les fameux "diviseurs de zéro"), ce qui casserait les preuves de sécurité. Le polynôme $X^n + 1$ est dit **cyclotomique** — une famille de polynômes aux propriétés algébriques très étudiées depuis le XIXe siècle, et qui donnent une structure particulièrement solide pour la cryptographie.

Au final, $R_q$ contient exactement tous les polynômes de degré $< n = 256$ à coefficients dans $\{0, 1, \ldots, 3328\}$. C'est dans cet espace que vivent toutes nos clés, nos erreurs et nos messages.

---

## 3) Le Problème au Cœur de Tout : LWE et Ring-LWE

*(La partie où on explique pourquoi c'est supposément incassable même avec un ordinateur quantique)*

### Mais d'abord, pourquoi on a besoin d'un nouveau problème difficile ?

RSA repose sur la difficulté de **factoriser** un grand entier. ECDH repose sur le **logarithme discret**. Ces deux problèmes sont solubles en temps polynomial par l'**algorithme de Shor** (Peter Shor, 1994) sur un ordinateur quantique. Le jour où un tel ordinateur existera à grande échelle, l'ensemble de la cryptographie actuelle tombe.

Ce n'est pas un problème futur abstrait. Des acteurs — étatiques notamment — interceptent et stockent dès aujourd'hui des communications chiffrées, en attendant d'avoir la puissance quantique pour les ouvrir. C'est l'attaque dite *"Harvest now, decrypt later"*. C'est pour ça que le NIST a lancé dès 2016 un processus de standardisation des algorithmes post-quantiques, aboutissant en 2024 à la publication de **ML-KEM** (NIST FIPS 203), dont ce projet est une implémentation simplifiée.

Il nous faut donc un problème que même un ordinateur quantique ne peut pas résoudre efficacement. C'est là qu'intervient LWE.

### Le problème LWE (*Learning With Errors*)

Introduit par Oded Regev en 2005 dans un article fondateur ([*On Lattices, Learning with Errors, Random Linear Codes, and Cryptography*](https://cims.nyu.edu/~regev/papers/qcrypto.pdf), STOC 2005), LWE est conceptuellement très simple.

Imaginons un secret $s \in \mathbb{Z}_q$. Quelqu'un vous donne des paires $(a_i,\, b_i)$ construites ainsi :

$$b_i = a_i \cdot s + e_i$$

avec $a_i$ tiré aléatoirement dans $\mathbb{Z}_q$ et $e_i$ un "petit" bruit. La question : pouvez-vous retrouver $s$ ?

- **Sans bruit** ($e_i = 0$) : trivial, $s = b_i / a_i$ (division possible car $q$ est premier).
- **Avec bruit** : Regev a démontré que ce problème est *au moins aussi difficile* que des problèmes géométriques sur les **réseaux euclidiens** (*lattices*), pour lesquels les meilleures attaques connues restent exponentielles en la dimension — y compris sur ordinateur quantique. C'est une **réduction de sécurité**, le Saint Graal en cryptographie : si quelqu'un casse LWE, il casse aussi ces problèmes de réseaux vieux de plusieurs décennies.

### Ring-LWE : la version efficace

LWE classique a un problème de performance : les clés sont des **matrices** de taille $n \times n$, soit $O(n^2)$ en espace et en temps. Pour $n = 256$, c'est gérable, mais pour atteindre un niveau de sécurité suffisant on voudrait $n$ bien plus grand.

**Ring-LWE** ([*On Ideal Lattices and Learning with Errors over Rings*](https://link.springer.com/article/10.1007/s00145-013-9155-2), Lyubashevsky, Peikert & Regev, EUROCRYPT 2010) résout ce problème en remplaçant les entiers par des polynômes dans $R_q$. Une seule équation :

$$b = a \cdot s + e \quad \text{dans } R_q$$

encode en réalité $n = 256$ équations LWE entrelacées à la fois, grâce à la structure multiplicative de l'anneau. On passe d'une complexité $O(n^2)$ à $O(n)$ en espace, et de $O(n^2)$ à $O(n \log n)$ en temps avec la NTT. C'est ce gain d'un facteur $n$ qui rend Kyber utilisable en pratique sur des cartes à puce ou dans TLS.

La sécurité reste (conjecturalement) aussi solide : distinguer $b = a \cdot s + e$ d'un polynôme purement aléatoire est aussi difficile que les problèmes de réseaux sous-jacents.

### La CBD : pourquoi ce bruit précisément ?

Pour que le chiffrement soit décryptable, le bruit $e$ doit être **petit**. Pour qu'il soit sûr, il doit être **statistiquement indiscernable d'un bruit gaussien**. La distribution naturelle serait donc une gaussienne discrète $D_\sigma$... mais il y a un problème.

Échantillonner une gaussienne discrète nécessite un **rejet conditionnel** : on tire un candidat, on teste s'il est acceptable, on recommence sinon. Le nombre d'itérations varie selon le tirage — et cette variation de temps est mesurable. C'est une **fuite d'information par canal auxiliaire** (*timing attack*), une vulnérabilité bien réelle en pratique.

La solution de Kyber, décrite dans la spec ([*CRYSTALS-Kyber v3.02*](https://pq-crystals.org/kyber/data/kyber-specification-round3-20210804.pdf)), est la **Centered Binomial Distribution** $\beta_\eta$. Pour chaque coefficient :

$$c = \sum_{j=1}^{\eta} a_j - \sum_{j=1}^{\eta} b_j, \qquad a_j, b_j \sim \text{Bernoulli}(1/2)$$

Le résultat est dans $[-\eta, +\eta]$, centré en $0$, avec variance $\eta/2$. Et surtout, l'algorithme est **constant-time** : on tire $2\eta$ bits, on fait deux sommes, on soustrait. Aucune branche conditionnelle, aucune boucle de rejet, aucune fuite temporelle.
```python
# cbd_sample() dans ring_lwe.py — remarquez : aucun if, aucune boucle de rejet
bits_a = rng.integers(0, 2, size=(n, eta))  # n×η bits
bits_b = rng.integers(0, 2, size=(n, eta))
coeffs = bits_a.sum(axis=1) - bits_b.sum(axis=1)  # dans [-η, +η], temps constant
```

---

## 4) Ce que dit le graphique

*(La partie où les maths rencontrent la réalité)*

Voici le résultat produit par `failure_rate_analysis.py` :

![Analyse du taux d'échec](Decryption%20Failure%20Rate%20Analysis.png)

Pour rappel, le principe du déchiffrement est le suivant. On calcule $w = v - s \cdot u$ et en développant algébriquement on obtient :

$$w = \underbrace{\left\lfloor \frac{q}{2} \right\rfloor \cdot m}_{\text{le signal}} \;+\; \underbrace{e \cdot r + e_2 - e_1 \cdot s}_{\varepsilon \text{ — le bruit résiduel}}$$

Le bit $m$ est correctement décodé si et seulement si le bruit résiduel $\varepsilon$ ne dépasse pas le seuil $q/4 \approx 832$. Au-delà, on se trompe de bit — c'est un **Decryption Failure**.

### Graphique A — La courbe DFR en fonction de $\eta$

Ce graphique trace le taux d'échec expérimental (points orange, 500 essais par valeur de $\eta$) contre la prédiction théorique par approximation gaussienne (courbe bleue).

La variance du bruit résiduel vaut $\text{Var}(\varepsilon) \approx \eta \cdot (n\eta + 1) / 2$. Avec $n = 256$ :

- Pour **$\eta = 2$ (Kyber)** : $\sigma \approx 22.6$. Le seuil $q/4 \approx 832$ est à **37 écarts-types** de la moyenne. DFR $< 2^{-139}$. On peut chiffrer des milliards de messages sans observer un seul échec — c'est pour ça qu'on voit 0% expérimentalement jusqu'à $\eta = 16$.

- **À partir de $\eta \approx 18$**, la transition s'amorce : 1.2% d'échecs expérimentaux, la courbe bleue prédit 1.1%. Les deux coïncident — ce n'est pas un hasard, ça valide que le modèle gaussien capte correctement la physique du bruit.

- Pour **$\eta = 22$** : 19.6% expérimental contre 19.2% théorique. Presque un message sur cinq est mal déchiffré.

- Pour **$\eta = 30$** : 95.4% d'échecs. Le système est complètement inutilisable.

Ce que la courbe montre visuellement c'est une **transition de phase** très nette autour de $\eta \approx 18$-$20$. En dessous : le système est fiable. Au-dessus : il s'effondre rapidement.

### Graphique B — La distribution du bruit résiduel

Ce graphique montre concrètement *pourquoi* la transition se produit, en traçant la distribution empirique de $\varepsilon[i]$ (tous les 256 coefficients de chaque bloc) pour trois régimes :

- **$\eta = 2$ (vert)** : la distribution est extrêmement concentrée autour de 0, avec un écart-type d'environ 22. Les deux lignes en pointillés à $\pm 832$ sont à une distance absurde — aucun coefficient n'approche jamais ce seuil. Résultat : DFR nul.

- **$\eta = 14$ (bleu)** : la distribution s'est élargie mais reste entièrement à l'intérieur des bornes $\pm 832$. On est encore dans la zone verte, juste un peu moins confortablement.

- **$\eta = 24$ (rouge)** : la distribution déborde largement au-delà des pointillés. Une proportion significative des coefficients dépasse le seuil de décision dans les deux sens — le décodage devient une loterie.

### Ce que ça signifie vraiment

Ce graphique reproduit, à micro-échelle, exactement le type d'analyse effectuée lors de la soumission de Kyber au NIST. Les concepteurs ont dû **prouver** que pour $\eta = 2$ et $n = 256$, le DFR est inférieur à $2^{-139}$ — une borne calculée non pas par simulation (on ne peut pas faire $2^{139}$ essais) mais par analyse exacte de la distribution de $\varepsilon$ via la transformée de Fourier de $\beta_\eta$.

C'est d'ailleurs le sujet de [*Failure is not an Option: Standardization Issues for Post-Quantum Key Encapsulation*](https://eprint.iacr.org/2019/1014.pdf) (D'Anvers, Karmakar, Roy, Vercauteren — EUROCRYPT 2018) : un article entier dédié à la question "comment calculer ce taux d'échec de façon exacte ?", parce que l'approximation gaussienne qu'on utilise ici peut sous-estimer le vrai DFR sur les queues de distribution.

En résumé : le paramètre $\eta$ n'est pas un détail d'implémentation. C'est le curseur fondamental entre sécurité et fiabilité, et choisir sa valeur est un vrai problème de recherche.