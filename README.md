# Cloudflare 优选 IP 自动生成

这个目录可以单独上传到一个新的 GitHub 仓库，用 GitHub Actions 定时运行 CloudflareSpeedTest，生成适合当前 `_worker.js` 使用的 `ADD.txt`。

> 注意：如果使用 GitHub 官方托管 runner，测速结果代表 `GitHub/Azure 机房 -> Cloudflare`，不等于你家宽/手机网络。想更准确，请使用 self-hosted runner 放在你的本地网络、软路由、NAS 或同运营商 VPS 上。

## 输出文件

运行后会生成：

- `output/result.csv`：CloudflareSpeedTest 原始结果
- `output/ADD.txt`：给本项目 KV `ADD.txt` 使用的优选 IP

`ADD.txt` 格式示例：

```txt
104.18.1.1:443#香港20.35MB/s`n172.67.1.1:443#美国15.2MB/s
```

你的 `_worker.js` 会把 `#` 后面的内容作为订阅节点名称。

## 默认定时

默认每 6 小时跑一次：

```yaml
cron: '0 */6 * * *'
```

你可以在 `.github/workflows/cfst.yml` 里修改。

常用写法：

```yaml
# 每 3 小时
cron: '0 */3 * * *'

# 每天北京时间 03:00，GitHub Actions 使用 UTC，所以是前一天 19:00 UTC
cron: '0 19 * * *'
```

## 使用方法

1. 把 `github-actions-cfst` 目录里的内容上传到一个 GitHub 仓库根目录。
2. 进入仓库 `Actions` 页面，启用 workflow。
3. 可以手动点 `Run workflow` 先跑一次。
4. 跑完后，在仓库的 `output/ADD.txt` 查看结果。
5. 把 `ADD.txt` 内容复制到你 Worker 管理面板的自定义优选 IP，或按你的方式写入 KV。

## 参数调整

在 `.github/workflows/cfst.yml` 里改这些环境变量：

| 变量 | 默认 | 说明 |
|---|---:|---|
| `CFST_PORT` | `443` | 测速端口 |
| `CFST_TOP` | `20` | 输出前多少个 IP |
| `CFST_TLS` | `true` | 是否测试 TLS |
| `CFST_TL` | `200` | 平均延迟上限，单位 ms |
| `CFST_DN` | `10` | 下载测速数量 |
| `CFST_MIN_SPEED` | `0` | 最低下载速度，单位 MB/s |

## 上传到 Worker KV 的选择

当前工作流默认只是提交 `output/ADD.txt` 到仓库，不直接操作 Cloudflare。

如果你想自动上传到 Cloudflare KV，需要额外配置 Cloudflare API Token / Account ID / Namespace ID。这个属于敏感凭据，我没有默认加入，避免误传密钥。

