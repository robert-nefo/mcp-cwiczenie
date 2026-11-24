# mcp-cwiczenie — kalkulator podsieci IPv4

Prosty kalkulator podsieci IPv4 napisany w czystym Pythonie (tylko biblioteka
standardowa). Oblicza parametry sieci dla podanego CIDR i dzieli sieć na
mniejsze podsieci.

## Funkcje

- **`calculate(cidr)`** — pełny opis sieci: adres sieci, maska, wildcard,
  broadcast, pierwszy/ostatni adres hostów, liczba adresów użytecznych,
  czy sieć jest prywatna.
- **`split(cidr, nowa_maska)`** — podział sieci na mniejsze podsieci
  (np. `/24` → cztery `/26`).
- Obsługa przypadków brzegowych zgodnie ze standardami:
  - `/31` — łącza punktowo-punktowe (RFC 3021): oba adresy są użytecznymi
    hostami,
  - `/32` — pojedynczy adres.

## Wymagania

Python ≥ 3.9 (żadne zależności zewnętrzne).

## Użycie z wiersza poleceń

```bash
# parametry sieci
python3 subnet.py 10.0.50.203/24

# parametry + podział na /26
python3 subnet.py 10.0.50.203/24 --split /26
```

Wynik jest wypisywany jako JSON. Kod błędu `2` oznacza nieprawidłowe dane
wejściowe.

## Przykład

```bash
$ python3 subnet.py 10.0.50.203/24 --split /26
{
  "network": {
    "network": "10.0.50.0",
    "prefix": 24,
    "mask": "255.255.255.0",
    "wildcard": "0.0.0.255",
    "broadcast": "10.0.50.255",
    "first_host": "10.0.50.1",
    "last_host": "10.0.50.254",
    "usable_hosts": 254,
    "total_addresses": 256,
    "is_private": true
  },
  "split": {
    "new_prefix": 26,
    "count": 4,
    "subnets": [
      "10.0.50.0/26",
      "10.0.50.64/26",
      "10.0.50.128/26",
      "10.0.50.192/26"
    ]
  }
}
```

## Testy

```bash
python3 -m unittest test_subnet -v
```

## Plik

- `subnet.py` — logika (`calculate`, `split`) + interfejs CLI.
