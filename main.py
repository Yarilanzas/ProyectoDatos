import argparse
from bench_personaD import correr_bench

def main():
    parser = argparse.ArgumentParser(description="Cliente del proyecto Cripta")

    parser.add_argument("--bench",action="store_true",help="Ejecuta las mediciones de persistencia binaria y JSON")

    argumentos = parser.parse_args()

    if argumentos.bench:
        correr_bench()
        return 0

    parser.print_help()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
