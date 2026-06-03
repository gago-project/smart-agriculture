// PM2 process supervisor for Smart Agriculture (process mode).
//
// Wraps the existing start scripts so all env/port logic is reused.
// IMPORTANT: restarts (crash or reboot) NEVER bump the version — these scripts
// only launch the already-built servers. Version bumping lives solely in the
// /deploy workflow.
//
//   pm2 start ecosystem.config.cjs   # bring both services under supervision
//   pm2 reload ecosystem.config.cjs  # zero-downtime-ish redeploy (used by /deploy)
//   pm2 ls | pm2 logs | pm2 monit    # observe
//   pm2 save                         # persist process list for resurrect/boot

const path = require('path');
const ROOT = __dirname;

// Shared crash-restart policy: auto-restart, but back off and give up on a
// crash loop so we don't spin forever on a genuinely broken build.
const common = {
  cwd: ROOT,
  interpreter: 'bash',
  autorestart: true,
  max_restarts: 10, // within min_uptime window -> then enters "errored", stops looping
  min_uptime: 15000, // must stay up 15s to count as a healthy start
  restart_delay: 3000, // wait 3s between restarts
  kill_timeout: 8000, // grace period for SIGINT before SIGKILL
  merge_logs: true,
  time: true, // prefix log lines with timestamps
};

module.exports = {
  apps: [
    {
      // Agent first: it writes .runtime/local-agent-port that web reads.
      ...common,
      name: 'sa-agent',
      script: path.join(ROOT, 'scripts/dev/start-local-agent.sh'),
      out_file: path.join(ROOT, '.runtime/logs/sa-agent.out.log'),
      error_file: path.join(ROOT, '.runtime/logs/sa-agent.err.log'),
    },
    {
      ...common,
      name: 'sa-web',
      script: path.join(ROOT, 'scripts/dev/start-local-web.sh'),
      out_file: path.join(ROOT, '.runtime/logs/sa-web.out.log'),
      error_file: path.join(ROOT, '.runtime/logs/sa-web.err.log'),
    },
  ],
};
