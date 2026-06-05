#!/bin/bash
# 餐饮差评AI工具 - 一键部署脚本
# 部署到 GitHub Pages / Vercel / Netlify

SITE_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "部署目录: $SITE_DIR"

# 检查文件
for f in landing_page.html README.md; do
    if [ ! -f "$SITE_DIR/$f" ]; then
        echo "缺少文件: $f"
        exit 1
    fi
done

echo "所有文件就绪。部署方式："
echo ""
echo "方式1 - Vercel（推荐，免费）:"
echo "  npx vercel --prod"
echo ""
echo "方式2 - Netlify:"
echo "  npx netlify-cli deploy --prod --dir=$SITE_DIR"
echo ""
echo "方式3 - GitHub Pages:"
echo "  1. 创建GitHub仓库"
echo "  2. git push到main分支"
echo "  3. Settings > Pages > 启用"
echo ""
echo "方式4 - Surge.sh（免费）:"
echo "  npx surge $SITE_DIR your-site-name.surge.sh"
