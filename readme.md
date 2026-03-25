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