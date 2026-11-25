# Sito Eratostenesa: liczby pierwsze mniejsze od 100.
def sieve(n):
    is_prime = [True] * n
    is_prime[0] = False
    is_prime[1] = False
    i = 2
    while i * i < n:
        if is_prime[i]:
            j = i * i
            while j < n:
                is_prime[j] = False
                j += i
        i += 1
    out = []
    for k in range(n):
        if is_prime[k]:
            out.append(k)
    return out

primes = sieve(100)
print(len(primes), "liczb pierwszych:")
print(primes)
