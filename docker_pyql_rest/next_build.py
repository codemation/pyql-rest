import sys

if __name__ == '__main__':
    tag, latest = sys.argv[1], sys.argv[2]
    tagId = float(latest.split(tag)[1])
    tagId+=0.01
    print(f"{tag}{tagId:.2f}")