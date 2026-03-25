from numpy.typing import NDArray
import numpy as np

N: int = 256      # Degré du polynôme
Q: int = 3329     # Modulus premier
ETA: int = 2      # Paramètre CBD (η = 2 dans Kyber-512)

# Valeur de "q/2" arrondie : seuil d'encodage du bit message
Q_HALF: int = Q // 2


# ══════════════════════════════════════════════════════════════════════
#  Arithmétique des polynômes dans R_q = Z_q[X]/(X^n + 1)
# ══════════════════════════════════════════════════════════════════════

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

        # Convolve c'est la multiplication clasie entre 2 plonymes 
        # Exemple : 2 + 3X = [2, 3] et 4 + 5X = [4, 5]
        # Donc convolve([2, 3], [4, 5]) = [8, 22, 15] (soit 8 + 22X + 15X^2).
        product = np.convolve(self.coeffs, other.coeffs)

        # Zeros crée un tableau de taille n rempli de 0 de 64 bytes.
        result = np.zeros(self.n, dtype=np.int64)

        #Processus espliquer dans la doc d la focntion 
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
    if rng is None:
        rng = np.random.default_rng()
    coeffs = rng.integers(0, q, size=n, dtype=np.int64)
    return RqPolynomial(coeffs, n, q)
