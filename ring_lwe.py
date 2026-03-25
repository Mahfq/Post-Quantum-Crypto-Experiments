from numpy.typing import NDArray
import numpy as np

N: int = 256      # Degré du polynôme
Q: int = 3329     # Modulus premier
ETA: int = 2      # Paramètre CBD (η = 2 dans Kyber-512)

# Valeur de "q/2" arrondie : seuil d'encodage du bit message
Q_HALF: int = Q // 2

#------------------------------------------------------------------#

class RqPolynomial:
    """
    Représente un élément de l'anneau R_q = Z_q[X] / (X^n + 1).

    Les coefficients sont stockés comme un tableau numpy d'entiers
    de longueur n, indexés du degré 0 au degré n-1.

    Toutes les opérations réduisent automatiquement :
        - les coefficients modulo q
        - le degré modulo (X^n + 1), c'est-à-dire X^n → −1
    """

    def __init__(self, coeffs: NDArray[np.int64], n: int = N, q: int = Q):
        self.n = n
        self.q = q

        c = np.asarray(coeffs, dtype=np.int64)
        assert c.shape == (n,), f"Attendu {n} coefficients, reçu {c.shape}"
        self.coeffs = c % q


    # Le "% self.q" dans add et sub est le Modulo. Il empêche les coefficients de dépasser q (3329).
    # Exemple : 3000 + 500 = 3500. Or 3500 > 3329 donc en modulo 3329, ça fait 3500 % 3329 = 171.

    def __add__(self, other: "RqPolynomial") -> "RqPolynomial":
        """Additionne deux polynômes coefficient par coefficient."""
        return RqPolynomial((self.coeffs + other.coeffs) % self.q, self.n, self.q)
    
    def __sub__(self, other: "RqPolynomial") -> "RqPolynomial":
        """Soustrait deux polynômes coefficient par coefficient."""
        return RqPolynomial((self.coeffs - other.coeffs) % self.q, self.n, self.q)


    # ── Multiplication ────────────────────────────────────────────────
    def __mul__(self, other: "RqPolynomial") -> "RqPolynomial":
        """
            Multiplication dans R_q = Z_q[X] / (X^n + 1).

            Algorithme (naïf, O(n^2)) :
            1. Convolution polynomiale classique -> degré 2n-2.
            2. Réduction modulo (X^n + 1) :
                pour tout k >= n :  coeff[k] * X^k
                                    = coeff[k] * X^{k-n} * X^n
                                    = -coeff[k] * X^{k-n}   (car X^n = -1)
            3. Réduction modulo q.

            Note : en pratique Kyber utilise la NTT pour descendre en O(n log n),
                mais la convolution numpy est suffisante ici pour la pédagogie.
        """

        # Convolve c'est la multiplication classique entre 2 polynômes 
        # Exemple : 2 + 3X = [2, 3] et 4 + 5X = [4, 5]
        # Donc convolve([2, 3], [4, 5]) = [8, 22, 15] (soit 8 + 22X + 15X^2).
        product = np.convolve(self.coeffs, other.coeffs)

        # Zeros crée un tableau de taille n rempli de 0 de 64 bits.
        result = np.zeros(self.n, dtype=np.int64)

        #Processus expliqué dans la doc de la fonction 
        for i, c in enumerate(product):
            if i < self.n:
                result[i] += c          #  X^i  →  X^i
            else:
                result[i - self.n] -= c #  X^i  →  −X^{i−n}

        return RqPolynomial(result % self.q, self.n, self.q)

    def __repr__(self) -> str:
        return f"RqPoly(n={self.n}, q={self.q}, coeffs[:8]={self.coeffs[:8]}...)"

    def __eq__(self, other: object) -> bool:
        #isinstance permet de vérifier que la variable 'other' est bien un polynôme (de type RqPolynomial).
        if not isinstance(other, RqPolynomial):
            return NotImplemented
        
        # array_equal vérifie si les 256 coeffs des 2 polynômes sont exactement les mêmes.
        return np.array_equal(self.coeffs, other.coeffs)


def zero_poly(n: int = N, q: int = Q) -> RqPolynomial:
    """Génère un polynôme dont tous les coefficients valent 0."""
    return RqPolynomial(np.zeros(n, dtype=np.int64), n, q)


def random_poly(n: int = N, q: int = Q, rng: np.random.Generator | None = None) -> RqPolynomial:
    # Si pas de fonction rng fournie, on en crée une par défaut pour le hasard.
    if rng is None:
        rng = np.random.default_rng()

    #On tire n nombres aléatoires compris entre 0 et q-1 
    coeffs = rng.integers(0, q, size=n, dtype=np.int64)
    return RqPolynomial(coeffs, n, q)

#------------------------------------------------------------------#

def cbd_sample(eta: int = ETA, n: int = N, q: int = Q, rng: np.random.Generator | None = None) -> RqPolynomial:
    """
    Échantillonne un polynôme "petit" depuis la distribution binomiale
    centrée (Centered Binomial Distribution).

    Pour chaque coefficient :
        On tire (a_1, ..., a_eta) et (b_1, ..., b_eta) qui valent 0 ou 1.
        Le coefficient final est la somme des a_i moins la somme des b_i.
    
    Cela permet de générer un bruit cryptographique très petit (compris entre 
    -eta et +eta) centré autour de 0, ce qui simule une courbe de Gauss.
    """
    
    # Si pas de fonction rng fournie, on en crée une par défaut pour le hasard.
    if rng is None:
        rng = np.random.default_rng()
    
    # On crée un tableau de n lignes et eta colonnes avec 0 ou 1 
    bits_a = rng.integers(0, 2, size=(n, eta), dtype=np.int64)
    bits_b = rng.integers(0, 2, size=(n, eta), dtype=np.int64)
    
    # sum(axis=1) permet de sommer tous les éléments de chaque ligne
    # Exemple si bits_a = [[1, 0], [1, 1],[0, 0]] => bits_a.sum(axis=1) = [1, 2, 0]
    coeffs = bits_a.sum(axis=1) - bits_b.sum(axis=1)
    
    return RqPolynomial(coeffs % q, n, q)

#------------------------------------------------------------------#

# ══════════════════════════════════════════════════════════════════════
#  ÉTAPE 3 — Primitives cryptographiques (KeyGen, Encrypt, Decrypt)
# ══════════════════════════════════════════════════════════════════════

def keygen(rng: np.random.Generator | None = None) -> tuple[
    tuple[RqPolynomial, RqPolynomial],  # Clé publique : (a, b)
    RqPolynomial                        # Clé privée : s
]:
    """
    Génère la paire de clés publique/privée.
    """
    if rng is None:
        rng = np.random.default_rng()

    a = random_poly(rng=rng)
    s = cbd_sample(rng=rng)
    e = cbd_sample(rng=rng)

    b = (a * s) + e
    return (a, b), s


def encrypt(pub_key: tuple[RqPolynomial, RqPolynomial], message_bits: list[int],
            rng: np.random.Generator | None = None) -> tuple[RqPolynomial, RqPolynomial]:
    """
    Chiffre une liste de bits (jusqu'à N=256 bits en un seul coup !).
    """
    if rng is None:
        rng = np.random.default_rng()

    a, b = pub_key 
    r = cbd_sample(rng=rng)
    e1 = cbd_sample(rng=rng)
    e2 = cbd_sample(rng=rng)

    # ENCODAGE DU MESSAGE :
    # Au lieu de mettre un seul bit dans la case 0, on parcourt la liste
    # et on range chaque bit dans sa propre case (coefficient).
    m_encoded = zero_poly()
    for i, bit in enumerate(message_bits):
        if bit == 1:
            m_encoded.coeffs[i] = Q_HALF

    u = (a * r) + e1
    v = (b * r) + e2 + m_encoded

    return u, v


def decrypt(ciphertext: tuple[RqPolynomial, RqPolynomial], priv_key: RqPolynomial, num_bits: int) -> list[int]:
    """
    Déchiffre un nombre précis de bits depuis le message chiffré.
    """
    u, v = ciphertext
    s = priv_key

    w = v - (s * u)

    decrypted_bits = []
    
    # On regarde les 'num_bits' premières cases de w pour retrouver notre liste
    for i in range(num_bits):
        val = w.coeffs[i]
        dist_0 = min(val, Q - val)
        dist_qhalf = abs(val - Q_HALF)
        
        decrypted_bits.append(1 if dist_qhalf < dist_0 else 0)

    return decrypted_bits


# ══════════════════════════════════════════════════════════════════════
#  TEST DU PROTOCOLE
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("--- Lancement du test Ring-LWE ---")
    

    print("Génération des clés...")
    pub_key, priv_key = keygen()
    print("Clés générées avec succès !")
    

    print(f"   [Aperçu de 'a' public] : {pub_key[0]}")
    print(f"   [Aperçu de 'b' public] : {pub_key[1]}")
    print(f"   [Aperçu de 's' secret] : {priv_key}\n")

    bits_a_envoyer = [1, 0, 1, 1, 0, 0, 1, 1]
    print(f"Message original envoyé : {bits_a_envoyer}")


    print("\nChiffrement en cours (ajout du bruit)...")
    ciphertext = encrypt(pub_key, bits_a_envoyer)

    print(f"   [Polynôme chiffré 'u'] : {ciphertext[0]}")
    print(f"   [Polynôme chiffré 'v'] : {ciphertext[1]}")


    print("\nDéchiffrement en cours (nettoyage du bruit)...")
    
    bits_decryptes = decrypt(ciphertext, priv_key, num_bits=len(bits_a_envoyer))
    print(f"Message déchiffré reçu : {bits_decryptes}\n")

    if bits_a_envoyer == bits_decryptes:
        print("SUCCÈS : Tous les bits ont survécu au bruit, l'ordinateur quantique peut aller se rhabiller !")
    else:
        print("ÉCHEC : Oups, le bruit a détruit le message.")