n = int(input())
arr = list(map(int, input().split()))
dp = [1 for _ in range(len(arr))]
max_len = 1
max_arr = arr[0]

for i in range(1,len(arr)):
    for j in range(i):
        if arr[i] > arr[j]:
            if dp[i] < dp[j]+1:
                dp[i] = dp[j]+1

print(max(dp))

