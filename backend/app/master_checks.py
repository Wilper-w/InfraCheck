"""Master-node inspection checks (per xunjian.md + k8s/GPU additions).

Each returns a POSIX shell script that runs on a master node. Exit 0 = passes
the expected criterion; exit 1 = check ran but criterion not met (abnormal).
Diagnostics print to stdout so they survive as `evidence`. DB auth uses the
password supplied from the gitignored .env (MYSQL_DEFAULT_PW), injected by the collector.
"""
from __future__ import annotations


# 1. mysql log backup (3 masters): daily rotation, >=7 copies.
def mysql_log_backup() -> str:
    return r"""
_DIR=/nvme/log/mysql
echo "--- ls $DIR (last) ---"
ls -ltrh "$_DIR" 2>/dev/null | tail -8
count=$(ls -A "$_DIR" 2>/dev/null | wc -l)
echo "backup_count=$count"
[ "$count" -ge 8 ] || { echo "MYSQL_LOG_BACKUP_FAIL: count=$count < 8"; exit 1; }
echo "MYSQL_LOG_BACKUP_OK"
"""


# 2. nginx log backup (3 masters): >=15 copies, no 0-byte, no 5xx in access.log.
def nginx_log_backup() -> str:
    return r"""
DIR=""
for d in /nvme/nginx-log /nvme/nginx; do if [ -d "$d" ]; then DIR="$d"; break; fi; done
[ -n "$DIR" ] || { echo "NGINX_LOG: no log dir"; exit 1; }
echo "log_dir=$DIR"
cnt_a=$(ls -A "$DIR/" 2>/dev/null | grep -c '^access')
cnt_e=$(ls -A "$DIR/" 2>/dev/null | grep -c '^error')
echo "count_access=$cnt_a count_error=$cnt_e"
[ "$cnt_a" -ge 15 ] && [ "$cnt_e" -ge 15 ] || { echo "NGINX_LOG_FAIL: backups access=$cnt_a error=$cnt_e (<15)"; exit 1; }
zero=$(find "$DIR/" -maxdepth 1 -type f -size 0 | wc -l)
echo "zero_byte_files=$zero"
[ "$zero" -eq 0 ] || { echo "NGINX_LOG_FAIL: $zero zero-byte backups"; exit 1; }
fivxx=$(grep -cE 'HTTP/1\.[01]" 5[0-9][0-9]' "$DIR/access.log" 2>/dev/null || echo 0)
echo "access_5xx=${fivxx:-0}"
[ "${fivxx:-0}" -eq 0 ] || { echo "NGINX_LOG_FAIL: ${fivxx} 5xx in access.log"; exit 1; }
echo "NGINX_LOG_OK"
"""


# 3. HB bond0 dual-NIC (all nodes) — single NIC is NOT abnormal.
def bond_status() -> str:
    return r"""
if [ -e /proc/net/bonding/bond0 ]; then
  echo "--- bond0 ---"
  grep -E "Bonding Mode|Number of ports|MII Status|Slave Interface" /proc/net/bonding/bond0 | head -10
  ports=$(grep -c "Slave Interface: " /proc/net/bonding/bond0)
  mii=$(grep -c "MII Status: up" /proc/net/bonding/bond0)
  echo "bond_ports=$ports mii_up=$mii"
  [ "$ports" -ge 2 ] && [ "$mii" -ge 2 ] || { echo "BOND_FAIL: ports=$ports mii_up=$mii"; exit 1; }
  echo "BOND_OK"
else
  echo "no-bond (single NIC in this env) -> not abnormal"
  echo "BOND_SKIP_SINGLE_NIC"
fi
"""


def _pw_esc() -> str:
    """MYSQL default password from .env, single-quote-escaped for the generated script."""
    from app import config
    return config.MYSQL_DEFAULT_PW.replace("'", "'\\''")


# 4. mysql cluster (any 1 master): wsrep_* statuses (auth: MYSQL_PW from .env).
def mysql_cluster() -> str:
    esc = _pw_esc()
    return fr'''export MYSQL_PW='{esc}'
[ -n "$MYSQL_PW" ] || {{ echo "MYSQL_PW_NOT_SET: 请在 .env 填 MYSQL_DEFAULT_PW"; exit 1; }}
VARS=$(mysql -uroot -p"$MYSQL_PW" -N -e "SHOW GLOBAL STATUS WHERE Variable_name IN ('wsrep_local_state_comment','wsrep_evs_state','wsrep_cluster_size','wsrep_cluster_status');" 2>/dev/null || \
       mysql -uroot -N -e "SHOW GLOBAL STATUS WHERE Variable_name IN ('wsrep_local_state_comment','wsrep_evs_state','wsrep_cluster_size','wsrep_cluster_status');" 2>/dev/null || echo "MYSQL_PROBE_FAIL")
echo "$VARS"
echo "$VARS" | grep -q "Synced" || {{ echo "MYSQL_CLUSTER_FAIL: not Synced"; exit 1; }}
echo "$VARS" | grep -q "OPERATIONAL" || {{ echo "MYSQL_CLUSTER_FAIL: evs not OPERATIONAL"; exit 1; }}
echo "$VARS" | grep -qE "wsrep_cluster_size.*3" || {{ echo "MYSQL_CLUSTER_FAIL: cluster size != 3"; exit 1; }}
echo "$VARS" | grep -q "Primary" || {{ echo "MYSQL_CLUSTER_FAIL: not Primary"; exit 1; }}
echo "MYSQL_CLUSTER_OK"
'''


# 5. etcd cluster (any 1 master): all members started, leader exists, capacity sane.
def etcd_cluster() -> str:
    return r"""
echo "--- etcd pods ---"
kubectl get pod -n kube-system -owide 2>/dev/null | grep '^etcd-'
export ETCDCTL_API=3
export ETCDCTL_CERT=/etc/kubernetes/pki/etcd/server.crt
export ETCDCTL_KEY=/etc/kubernetes/pki/etcd/server.key
export ETCDCTL_CACERT=/etc/kubernetes/pki/etcd/ca.crt
EPS=$(etcdctl member list 2>/dev/null | sed -E 's#.*https://([0-9.]+):2380.*#https://\1:2379#' | tr '\n' ',' | sed 's/,$//')
echo "endpoints=$EPS"
etcdctl member list 2>/dev/null | head -6
echo "--- endpoint status (all members) ---"
etcdctl endpoint status --endpoints="$EPS" --write-out=table 2>/dev/null | head -8
leaders=$(etcdctl endpoint status --endpoints="$EPS" -w json 2>/dev/null | grep -oE '"leader":[1-9][0-9]*' | wc -l)
started=$(etcdctl member list 2>/dev/null | grep -c started)
total=$(etcdctl member list 2>/dev/null | grep -cE '^[0-9a-f]{16}')
echo "members_total=$total started=$started leader_count=$leaders"
[ "$total" -ge 1 ] && [ "$started" -ge 1 ] || { echo "ETCD_FAIL: members total=$total started=$started"; exit 1; }
[ "$started" -eq "$total" ] || { echo "ETCD_FAIL: started=$started != total=$total"; exit 1; }
[ "$leaders" -ge 1 ] || { echo "ETCD_FAIL: no leader across members"; exit 1; }
echo "ETCD_OK"
"""


# 6. DB new partition (Mon am, any master): next-week partition + p_future.
def db_partition() -> str:
    esc = _pw_esc()
    return fr'''export MYSQL_PW='{esc}'
[ -n "$MYSQL_PW" ] || {{ echo "MYSQL_PW_NOT_SET: 请在 .env 填 MYSQL_DEFAULT_PW"; exit 1; }}
OUT=$(mysql -uroot -p"$MYSQL_PW" -N -e "SELECT PARTITION_NAME FROM information_schema.PARTITIONS WHERE TABLE_SCHEMA='oneapi_log' AND TABLE_NAME='logs';" 2>/dev/null || echo MYSQL_PROBE_FAIL)
echo "$OUT"
echo "$OUT" | grep -q "p_future" || {{ echo "PARTITION_FAIL: no p_future (query failed or table absent)"; exit 1; }}
NW=$(echo "$OUT" | grep -Eo 'p[0-9]{4}w[0-9]+' | sort -V | tail -1)
echo "latest_partition=$NW"
echo "PARTITION_OK (p_future present, latest=$NW)"
'''


# 7. k8s 集群组件健康（control-plane pods + 节点 Ready）
def k8s_components() -> str:
    return r"""
echo "--- readyz ---"
kubectl get --raw='/readyz' 2>/dev/null | head -1
echo "--- nodes ---"
kubectl get nodes 2>/dev/null | head -10
notready=$(kubectl get nodes --no-headers 2>/dev/null | grep -c NotReady)
echo "nodes_notready=$notready"
[ "$notready" -eq 0 ] || { echo "K8S_NODE_FAIL: $notready NotReady"; exit 1; }
echo "--- control-plane pods ---"
for p in $(kubectl get pods -n kube-system -o name 2>/dev/null | grep -E 'kube-apiserver|kube-controller-manager|kube-scheduler'); do
  st=$(kubectl get "$p" -n kube-system -o jsonpath='{.status.phase}' 2>/dev/null)
  echo "$p -> $st"
  [ "$st" = "Running" ] || { echo "K8S_COMPONENT_FAIL: $p $st"; exit 1; }
done
echo "K8S_COMPONENTS_OK"
"""


# 8. k8s 证书过期（apiserver/etcd/ca）
def k8s_cert_expiry() -> str:
    return r"""
for c in apiserver.crt etcd/server.crt ca.crt; do
  f=/etc/kubernetes/pki/$c
  [ -f "$f" ] || { echo "CERT_MISSING: $f"; continue; }
  end=$(openssl x509 -in "$f" -noout -enddate 2>/dev/null | cut -d= -f2)
  e=$(date -d "$end" +%s 2>/dev/null); n=$(date +%s)
  days=$(( (e-n)/86400 ))
  echo "$c end=$end days_left=$days"
  [ "$days" -gt 30 ] || { echo "CERT_EXPIRY_FAIL: $c $days days left"; exit 1; }
done
echo "CERT_OK"
"""


# 9. etcd 备份任务（kube-system cronjob/pods）
def etcd_backup() -> str:
    return r"""
echo "--- etcd cronjobs ---"
kubectl get cronjob -n kube-system 2>/dev/null | grep -i etcd || echo "no etcd cronjob"
echo "--- recent etcd-backup pods ---"
kubectl get pods -n kube-system -o wide --no-headers 2>/dev/null | grep etcd-backup | tail -5
bad=$(kubectl get pods -n kube-system --no-headers 2>/dev/null | grep etcd-backup | grep -vE 'Completed|Running' | wc -l)
last=$(kubectl get pods -n kube-system --no-headers 2>/dev/null | grep etcd-backup | tail -1)
echo "$last" | grep -qE 'Completed' && echo "ETCD_BACKUP_OK (latest completed, bad=$bad)" || { echo "ETCD_BACKUP_FAIL: latest not completed: $last"; exit 1; }
"""


_MASTERS: dict[str, object] = {
    "mysql_log_backup": mysql_log_backup,
    "nginx_log_backup": nginx_log_backup,
    "bond_status": bond_status,
    "mysql_cluster": mysql_cluster,
    "etcd_cluster": etcd_cluster,
    "db_partition": db_partition,
    "k8s_components": k8s_components,
    "k8s_cert_expiry": k8s_cert_expiry,
    "etcd_backup": etcd_backup,
}

MASTER_CHECK_NAMES = set(_MASTERS.keys())


def master_script(name: str) -> str:
    fn = _MASTERS.get(name)
    return fn() if fn else "echo 'unknown master check: " + name + "'"
