import asyncio
import cProfile
import pstats
import endpoint

def main():
    with cProfile.Profile() as pr:
        # do something here
        pass
    
    with open("stats.txt", "w") as s:
        stats = pstats.Stats(pr, stream= s)
        stats.sort_stats(pstats.SortKey.TIME)
        stats.print_stats()

if __name__ == "__main__":
    main()