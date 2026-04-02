# Pencil MCP 测试计划

## 测试环境检查清单

- [ ] Pencil 应用程序已安装到 /Applications
- [ ] MCP 服务器二进制文件存在且可执行
- [ ] Pencil 应用程序已启动
- [ ] MCP 服务器能正确初始化
- [ ] MCP 工具调用正常

## 测试步骤

### 1. 前置检查
```bash
# 验证 MCP 服务器存在
ls -la "/Applications/Pencil.app/Contents/Resources/app.asar.unpacked/out/mcp-server-darwin-arm64"

# 检查文件类型
file "/Applications/Pencil.app/Contents/Resources/app.asar.unpacked/out/mcp-server-darwin-arm64"
```

### 2. 启动 Pencil 应用程序
1. 打开 Finder → 应用程序 → Pencil
2. 或者运行：`open /Applications/Pencil.app`
3. 确保 Pencil 完全启动（看到主界面）

### 3. 配置 MCP 客户端
在支持 MCP 的客户端（如 Claude Desktop、Cursor 等）中添加配置：

```json
{
  "mcpServers": {
    "pencil": {
      "command": "/Applications/Pencil.app/Contents/Resources/app.asar.unpacked/out/mcp-server-darwin-arm64",
      "args": [],
      "env": {}
    }
  }
}
```

### 4. 验证 MCP 连接
重启 MCP 客户端后，检查：
- [ ] 客户端显示 Pencil MCP 服务器已连接
- [ ] 可用工具列表中包含 Pencil 相关工具
- [ ] 可以成功调用 Pencil 工具

### 5. 功能测试
测试以下功能（根据 Pencil MCP 实际提供的能力）：
- [ ] 创建新文档
- [ ] 打开现有文档
- [ ] 导出图表
- [ ] 获取文档列表
- [ ] 其他 Pencil 特定功能

## 故障排除

### 如果 MCP 服务器无法启动：
1. 检查 Pencil 应用程序是否已完全启动
2. 检查是否有防火墙阻止连接
3. 查看 Pencil 应用程序日志
4. 尝试重新安装 Pencil

### 如果 MCP 客户端无法连接：
1. 确认配置文件路径正确
2. 重启 MCP 客户端
3. 检查客户端日志中的错误信息

## 预期结果

✅ **成功状态：**
- MCP 服务器启动无错误
- 客户端显示 Pencil 工具可用
- 可以成功调用 Pencil 功能

❌ **失败状态：**
- ENOENT 错误（文件不存在）
- "app connection is required" 错误（Pencil 未启动）
- 权限错误（需要检查文件权限）
