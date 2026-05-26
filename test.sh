#!/bin/bash
set -euo pipefail

PF_CONF="/etc/pf.conf"
ANCHOR_FILE="/etc/pf.anchors/custom"
BACKUP_SUFFIX="$(date +%Y%m%d_%H%M%S)"
TMP_FILE="$(mktemp)"

IFACE="en0"
LOCAL_IP="192.168.31.27"
LISTEN_PORT="12345"
TARGET_PORT="445"

echo "[1/7] 检查 root 权限..."
if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 sudo 运行此脚本"
  exit 1
fi

echo "[2/7] 备份 pf.conf..."
cp "${PF_CONF}" "${PF_CONF}.bak.${BACKUP_SUFFIX}"
echo "已备份到: ${PF_CONF}.bak.${BACKUP_SUFFIX}"

echo "[3/7] 写入 anchor 文件 ${ANCHOR_FILE} ..."
cat > "${ANCHOR_FILE}" <<EOF
rdr on ${IFACE} inet proto tcp from any to ${LOCAL_IP} port ${LISTEN_PORT} -> ${LOCAL_IP} port ${TARGET_PORT}
pass in on ${IFACE} inet proto tcp from any to ${LOCAL_IP} port {${LISTEN_PORT}, ${TARGET_PORT}} keep state
EOF

echo "[4/7] 按位置更新 ${PF_CONF} ..."

awk '
BEGIN {
  added_rdr=0
  added_anchor=0
  added_load=0
}
{
  print $0

  if ($0 == "rdr-anchor \"com.apple/*\"" && !added_rdr) {
    print "rdr-anchor \"custom\""
    added_rdr=1
  }

  if ($0 == "anchor \"com.apple/*\"" && !added_anchor) {
    print "anchor \"custom\""
    added_anchor=1
  }

  if ($0 == "load anchor \"com.apple\" from \"/etc/pf.anchors/com.apple\"" && !added_load) {
    print "load anchor \"custom\" from \"/etc/pf.anchors/custom\""
    added_load=1
  }
}
END {
  if (!added_rdr) {
    print "ERROR: 未找到 rdr-anchor \"com.apple/*\"" > "/dev/stderr"
    exit 1
  }
  if (!added_anchor) {
    print "ERROR: 未找到 anchor \"com.apple/*\"" > "/dev/stderr"
    exit 1
  }
  if (!added_load) {
    print "ERROR: 未找到 load anchor \"com.apple\" from \"/etc/pf.anchors/com.apple\"" > "/dev/stderr"
    exit 1
  }
}
' "${PF_CONF}" > "${TMP_FILE}"

# 如果已存在 custom 行，避免重复插入
if grep -q '^rdr-anchor "custom"$' "${PF_CONF}" || \
   grep -q '^anchor "custom"$' "${PF_CONF}" || \
   grep -q '^load anchor "custom" from "/etc/pf.anchors/custom"$' "${PF_CONF}"; then
  echo "检测到 ${PF_CONF} 已存在 custom 配置，跳过插入。"
else
  cp "${TMP_FILE}" "${PF_CONF}"
  echo "已插入 custom anchor 配置。"
fi

rm -f "${TMP_FILE}"

echo "[5/7] 校验 PF 配置..."
pfctl -nf "${PF_CONF}"

echo "[6/7] 重载 PF 配置..."
pfctl -f "${PF_CONF}"

echo "[7/7] 启用 PF（若未启用）..."
pfctl -e || true

echo
echo "当前 rdr 规则:"
pfctl -sn || true

echo
echo "当前 filter 规则:"
pfctl -sr || true

echo
echo "完成。可测试：nc -vz ${LOCAL_IP} ${LISTEN_PORT}"
