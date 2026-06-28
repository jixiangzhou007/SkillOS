# Sprint 7–8 · HA 双节点部署

## 目标

API 无单点；SQLite 数据目录共享或迁移 PostgreSQL（生产推荐后者）。

## 方案 A：双 API + 共享存储（试点）

```yaml
# docker-compose.ha.yml
services:
  skillos-a:
    image: skillos:latest
    environment:
      - SKILLOS_DATA_DIR=/data
      - SKILLOS_JWT_SECRET=${JWT_SECRET}
    volumes:
      - skillos-data:/data
    ports: ["8765:8765"]

  skillos-b:
    image: skillos:latest
    environment:
      - SKILLOS_DATA_DIR=/data
      - SKILLOS_JWT_SECRET=${JWT_SECRET}
    volumes:
      - skillos-data:/data
    ports: ["8766:8765"]

  nginx:
    image: nginx:alpine
    ports: ["443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on: [skillos-a, skillos-b]

volumes:
  skillos-data:
```

`nginx.conf` 上游 `skillos-a:8765` + `skillos-b:8765`，`least_conn` 负载均衡。

## 方案 B：MCP 分离

- 节点 1：FastAPI + 前端
- 节点 2：`python -m skillos.mcp_server`（只读 skills 目录同步）

## 健康检查

```bash
curl http://localhost:8765/health
curl http://localhost:8765/api/analytics/stability
```

## 注意事项

- **SQLite**：多写节点需 WAL + 共享 NFS/EBS；高并发建议 PostgreSQL migration（Sprint 9+）
- **JWT_SECRET** 两节点必须一致
- **Evolution scheduler**：仅单节点启用（`SKILLOS_EVOLUTION_LEADER=1`）

## 验证清单

- [ ] 两节点 `/health` 均 200
- [ ] 登录 JWT 在任一节点有效
- [ ] kill 一节点后 nginx  failover 成功
