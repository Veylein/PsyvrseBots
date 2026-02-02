/*
  PsySource Render Webhook -> Discord bot

  - Express webhook endpoint that validates requests using HMAC-SHA256 with
    the `RENDER_WEBHOOK_SECRET` value.
  - Fetches the first ~1900 characters of logs (uses RENDER_API_KEY if provided)
  - Sends a polished embed to a Discord channel using discord.js v14
  - Pings a failure role on deploy failures

  Usage:
    - Copy `.env.example` to `.env` and fill values
    - `npm install` then `node index.js`
*/

import express from 'express'
import dotenv from 'dotenv'
import crypto from 'crypto'
import fs from 'fs'
import { Client, GatewayIntentBits, EmbedBuilder, PermissionsBitField } from 'discord.js'
import { exec } from 'child_process'

dotenv.config()

const {
  PSYVERSE_TOKEN,
  LOG_CHANNEL,
  RENDER_WEBHOOK_SECRET,
  RENDER_API_KEY,
  PORT = 3000,
  FAILURE_ROLE_ID,
  SILENCE_SUCCESS = 'false',
  PSY_OWNER_IDS = '1382187068373074001,1311394031640776716,1300838678280671264,1138720397567742014',
} = process.env

const SILENCE_OK = String(SILENCE_SUCCESS).toLowerCase() === 'true'

// Validate important environment variables early to fail fast with clear messages
function isPlaceholder(value) {
  if (!value) return true
  const s = String(value).toLowerCase()
  return /your_|example|replace|xxx|changeme/.test(s)
}

// Runtime config persistence (allows updating LOG_CHANNEL without restarting)
const RUNTIME_CONFIG_FILE = './runtime_config.json'
function loadRuntimeConfig() {
  try {
    if (!fs.existsSync(RUNTIME_CONFIG_FILE)) return {}
    const raw = fs.readFileSync(RUNTIME_CONFIG_FILE, 'utf8')
    return JSON.parse(raw || '{}')
  } catch (e) {
    console.error('Failed to load runtime config:', e)
    return {}
  }
}

function saveRuntimeConfig(cfg) {
  try {
    fs.writeFileSync(RUNTIME_CONFIG_FILE, JSON.stringify(cfg, null, 2), 'utf8')
    return true
  } catch (e) {
    console.error('Failed to save runtime config:', e)
    return false
  }
}

// Small HTML/escaping helpers used to update the repo GitHub page
function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function buildUpdateHtml(messageText, authorTag, when) {
  const body = escapeHtml(messageText).replace(/\n/g, '<br>')
  const ts = (when instanceof Date) ? when.toISOString() : String(when)
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Latest Update</title>
    <style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;max-width:900px;margin:40px auto;padding:0 16px;color:#111} .meta{color:#666;margin-bottom:8px} .card{border-radius:8px;padding:18px;background:#f6f8fa;border:1px solid #e1e4e8}</style>
  </head>
  <body>
    <h1>Latest Update</h1>
    <div class="meta">Posted by ${escapeHtml(authorTag)} on ${escapeHtml(ts)}</div>
    <div class="card">${body}</div>
  </body>
</html>`
}

function getLogChannelId() {
  const runtime = loadRuntimeConfig()
  return runtime.log_channel || LOG_CHANNEL
}

function setLogChannelId(id) {
  const runtime = loadRuntimeConfig()
  runtime.log_channel = String(id)
  return saveRuntimeConfig(runtime)
}

const requiredEnv = {
  PSYVERSE_TOKEN,
  LOG_CHANNEL,
  RENDER_WEBHOOK_SECRET,
}

const missing = Object.entries(requiredEnv).filter(([_k, v]) => isPlaceholder(v)).map(([k]) => k)
if (missing.length) {
  console.error('Missing or placeholder environment variables:', missing.join(', '))
  console.error('Please update the .env file with real values before starting the bot.')
  process.exit(1)
}

// Colors
const COLORS = {
  succeeded: 0x2ecc71, // green
  failed: 0xe74c3c, // red
  started: 0xf1c40f, // yellow
}

// Emoji by status
const EMOJI = {
  succeeded: '✅',
  failed: '❌',
  started: '⚡',
}

// Discord client — include message intents so the bot can respond to prefix commands
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] })

client.once('ready', () => {
  console.log(`Discord client ready: ${client.user.tag} (${client.user.id})`)
})

// Prefix command handler (simple, for a private server)
const PREFIX = '$'
const FEEDBACK_CHANNEL_ID = process.env.FEEDBACK_CHANNEL_ID || '1465194346784751827'

const BLACKLIST_FILE = './feedback_blacklist.json'

function loadFeedbackBlacklist() {
  try {
    if (!fs.existsSync(BLACKLIST_FILE)) return []
    const raw = fs.readFileSync(BLACKLIST_FILE, 'utf8')
    return JSON.parse(raw || '[]')
  } catch (e) {
    console.error('Failed to load feedback blacklist:', e)
    return []
  }
}

function saveFeedbackBlacklist(list) {
  try {
    fs.writeFileSync(BLACKLIST_FILE, JSON.stringify(list, null, 2), 'utf8')
    return true
  } catch (e) {
    console.error('Failed to save feedback blacklist:', e)
    return false
  }
}

// owners from env (comma-separated ids)
const OWNER_IDS = new Set((PSY_OWNER_IDS || '').split(',').map(s => s.trim()).filter(Boolean))

function isOwner(userId) {
  if (OWNER_IDS.size > 0) return OWNER_IDS.has(String(userId))
  // fallback: compare to application owner when available
  try {
    const appOwner = client.application?.owner?.id
    if (appOwner) return String(userId) === String(appOwner)
  } catch (e) {
    // ignore
  }
  return false
}

client.on('messageCreate', async (message) => {
  try {
    if (!message.guild) return // ignore DMs
    if (message.author.bot) return
    if (!message.content.startsWith(PREFIX)) return

    const [rawCmd, ...rest] = message.content.slice(PREFIX.length).trim().split(/\s+/)
    const cmd = rawCmd.toLowerCase()
    const args = rest.join(' ')

    // permission check helper
    const hasManage = message.member && message.member.permissions && message.member.permissions.has(PermissionsBitField.Flags.ManageMessages)

    if (cmd === 'say') {
      if (!hasManage) return message.reply('You need Manage Messages permission to use this command.')
      if (!args) return message.reply('Usage: $say <message>')
      await message.channel.send(args)
      return
    }

    if (cmd === 'embed') {
      if (!hasManage) return message.reply('You need Manage Messages permission to use this command.')
      if (!args) return message.reply('Usage: $embed <title> | <description>')
      // split on first | to separate title and description
      const parts = args.split('|')
      const title = parts.shift().trim()
      const description = parts.join('|').trim() || '\u200b'
      const eb = new EmbedBuilder().setTitle(title).setDescription(description).setTimestamp().setColor(0x3498db).setFooter({ text: `Posted by ${message.author.tag}` })
      await message.channel.send({ embeds: [eb] })
      return
    }

    if (cmd === 'update') {
      if (!hasManage) return message.reply('You need Manage Messages permission to use this command.')
      if (!args) return message.reply('Usage: $update <message>')
      const eb = new EmbedBuilder().setDescription(args).setTimestamp().setColor(0x3498db).setFooter({ text: `Posted by ${message.author.tag}` })
      await message.channel.send({ embeds: [eb] })
      try {
        const html = buildUpdateHtml(args, message.author.tag, new Date())
        fs.writeFileSync('./update.html', html, 'utf8')
      } catch (e) {
        console.error('Failed to write update.html', e)
      }
      return
    }

    if (cmd === 'feedback') {
      if (!args) return message.reply('Usage: $feedback <your message>')
      const blacklist = loadFeedbackBlacklist()
      if (blacklist.includes(String(message.author.id))) return message.reply('You are not allowed to send feedback.')
      const targetChannel = await client.channels.fetch(FEEDBACK_CHANNEL_ID).catch(() => null)
      if (!targetChannel) {
        console.error('Feedback target channel not available')
        return message.reply('Feedback cannot be delivered at this time.')
      }
      const fb = new EmbedBuilder()
        .setTitle('User Feedback')
        .addFields(
          { name: 'From', value: `${message.author.tag} (${message.author.id})`, inline: false },
          { name: 'Server', value: `${message.guild.name} (${message.guild.id})`, inline: true },
          { name: 'Channel', value: `${message.channel.name} (${message.channel.id})`, inline: true },
          { name: 'Message', value: args.slice(0, 1900) }
        )
        .setTimestamp()
        .setColor(0x9b59b6)
      await targetChannel.send({ embeds: [fb] })
      await message.reply('Thanks — your feedback has been sent to the team.')
      return
    }

    // Feedback blacklist management (owners only)
    if (cmd === 'feedback_blacklist') {
      const [sub, id] = rest
      if (!isOwner(message.author.id)) return message.reply('Only bot owners can manage the feedback blacklist.')
      const list = loadFeedbackBlacklist()
      if (sub === 'add') {
        if (!id) return message.reply('Usage: $feedback_blacklist add <user_id>')
        if (!list.includes(id)) list.push(id)
        saveFeedbackBlacklist(list)
        return message.reply(`Added ${id} to feedback blacklist.`)
      }
      if (sub === 'remove') {
        if (!id) return message.reply('Usage: $feedback_blacklist remove <user_id>')
        const idx = list.indexOf(id)
        if (idx !== -1) list.splice(idx, 1)
        saveFeedbackBlacklist(list)
        return message.reply(`Removed ${id} from feedback blacklist.`)
      }
      if (sub === 'list') {
        return message.reply(`Feedback blacklist: ${list.length ? list.join(', ') : '(empty)'}`)
      }
      return message.reply('Usage: $feedback_blacklist <add|remove|list> [user_id]')
    }

    // Audit command - quick health checks
    if (cmd === 'audit') {
      // permission: require owner or ManageMessages
      if (!isOwner(message.author.id) && !hasManage) return message.reply('You need Manage Messages or owner access to run audit.')
      const checks = []
      // env checks
      const envs = ['PSYVERSE_TOKEN', 'LOG_CHANNEL', 'RENDER_WEBHOOK_SECRET', 'FEEDBACK_CHANNEL_ID']
      for (const e of envs) {
        const v = process.env[e]
        checks.push(`${e}: ${v ? 'OK' : 'MISSING'}`)
      }
      // blacklist count
      const bl = loadFeedbackBlacklist()
      checks.push(`Feedback blacklist entries: ${bl.length}`)
      // channel availability
      try {
        const logCh = await client.channels.fetch(getLogChannelId()).catch(() => null)
        checks.push(`Log channel fetch: ${logCh ? 'OK' : 'FAILED'}`)
      } catch (e) {
        checks.push('Log channel fetch: ERROR')
      }
      return message.reply(`Audit results:\n${checks.join('\n')}`)
    }
  } catch (err) {
    console.error('Error handling message command:', err)
  }
})

if (PSYVERSE_TOKEN) {
  client.login(PSYVERSE_TOKEN).catch(err => {
    console.error('Failed to login Discord client:', err)
  })
} else {
  console.warn('PSYVERSE_TOKEN not set; bot will not post to Discord until set')
}

const app = express()

// capture raw body for HMAC verification
app.use(express.json({ verify: (req, _res, buf) => { req.rawBody = buf } }))

function timingSafeEqualHex(a, b) {
  try {
    const ab = Buffer.from(a, 'hex')
    const bb = Buffer.from(b, 'hex')
    if (ab.length !== bb.length) return false
    return crypto.timingSafeEqual(ab, bb)
  } catch (e) {
    return false
  }
}

function verifySignature(secret, rawBody, headerValue) {
  if (!headerValue) return false
  // Accept formats like 'sha256=<hex>' or raw hex
  const received = headerValue.includes('=') ? headerValue.split('=')[1] : headerValue
  const h = crypto.createHmac('sha256', secret).update(rawBody).digest('hex')
  return timingSafeEqualHex(h, received)
}

async function fetchLogsSnippet(logsUrl) {
  if (!logsUrl) return 'No logs URL provided.'
  try {
    const headers = {}
    if (RENDER_API_KEY) headers['Authorization'] = `Bearer ${RENDER_API_KEY}`
    const resp = await fetch(logsUrl, { headers })
    if (!resp.ok) return `Failed to fetch logs (status ${resp.status})`
    const text = await resp.text()
    // Trim to 1900 chars to fit into a 2k Discord message (we add code fences too)
    const trimmed = text.slice(0, 1900)
    return trimmed + (text.length > 1900 ? '\n\n...(logs truncated)' : '')
  } catch (err) {
    console.error('Error fetching logs:', err)
    return `Error fetching logs: ${err.message}`
  }
}

function extractPayload(payload) {
  // Try common Render webhook shapes but stay defensive
  const serviceName = payload.service?.name || payload.service_name || payload.service || (payload.service && payload.service.name) || 'unknown'
  const commit = payload.commit?.sha || payload.commit?.hash || payload.commit || payload.commit_hash || payload.revision || payload.sha || payload.commitId || null
  const status = payload.status || payload.deploy?.status || payload.build?.status || payload.event || (payload.state) || 'unknown'
  const logsUrl = payload.logs_url || payload.log_url || payload.build?.logs_url || payload.deploy?.logs_url || payload.logs
  return { serviceName, commit, status: String(status).toLowerCase(), logsUrl }
}

app.post('/render-webhook', async (req, res) => {
  try {
    // Validate signature
    if (!RENDER_WEBHOOK_SECRET) {
      console.error('RENDER_WEBHOOK_SECRET not set; rejecting webhook for safety')
      return res.status(500).send('Server not configured')
    }

    const sigHeader = req.headers['render-signature'] || req.headers['x-render-signature'] || req.headers['render-signature-sha256']
    if (!verifySignature(RENDER_WEBHOOK_SECRET, req.rawBody || Buffer.from(''), String(sigHeader || ''))) {
      console.warn('Invalid webhook signature, rejecting')
      return res.status(401).send('Invalid signature')
    }

    const payload = req.body
    const { serviceName, commit, status, logsUrl } = extractPayload(payload)

    // Map status to visual
    const statusKey = status.includes('success') || status === 'succeeded' || status === 'success' ? 'succeeded' : (status.includes('fail') || status === 'failed' ? 'failed' : 'started')

    if (SILENCE_OK && statusKey === 'succeeded') {
      console.log(`Silencing success for ${serviceName}`)
      return res.status(204).send()
    }

    // Fetch logs snippet (non-blocking fetch but we await)
    const logsSnippet = await fetchLogsSnippet(logsUrl)

    // Build embed
    const embed = new EmbedBuilder()
      .setTitle(`${EMOJI[statusKey] || ''} ${serviceName} — ${statusKey.toUpperCase()}`)
      .setColor(COLORS[statusKey] || COLORS.started)
      .addFields(
        { name: 'Commit', value: commit ? `\`${String(commit).slice(0, 12)}\`` : 'unknown', inline: true },
        { name: 'Status', value: status || 'unknown', inline: true },
      )
      .setTimestamp(new Date())
      .setFooter({ text: 'Render Deploy Notification' })

    if (logsUrl) embed.setURL(logsUrl)

    // Send to channel (prefer runtime-configured channel)
    const resolvedLogChannel = getLogChannelId()
    if (!resolvedLogChannel) {
      console.error('LOG_CHANNEL not set; cannot post message')
      return res.status(500).send('Discord channel not configured')
    }

    const channel = await client.channels.fetch(resolvedLogChannel).catch(e => null)
    if (!channel) {
      console.error('Failed to fetch channel with id', LOG_CHANNEL)
      return res.status(500).send('Discord channel not available')
    }

    // Compose message content: ping on failures, include logs as code block in content (up to 1900 chars)
    let content = ''
    if (statusKey === 'failed' && FAILURE_ROLE_ID) content = `<@&${FAILURE_ROLE_ID}> `
    // Attach logs snippet in message content as code block (ensures we respect embed field limits)
    if (logsSnippet) content += `\n\n\`\`\`\n${logsSnippet}\n\`\`\``

    try {
      await channel.send({ content: content || undefined, embeds: [embed] })
    } catch (err) {
      console.error('Failed to send message to Discord:', err)
      return res.status(500).send('Failed to post to Discord')
    }

    return res.status(200).send('OK')
  } catch (err) {
    console.error('Unhandled error in webhook handler:', err)
    return res.status(500).send('Server error')
  }
})

app.get('/', (_req, res) => res.send('PsySource Render Webhook Bot is running'))

app.listen(Number(PORT), () => {
  console.log(`PsySource webhook listening on port ${PORT}`)
})

// Register slash commands and interaction handlers
import { SlashCommandBuilder, PermissionFlagsBits, ContextMenuCommandBuilder, ApplicationCommandType } from 'discord.js'
import translate from '@vitalets/google-translate-api'

const DEV_GUILD_ID = process.env.DEV_GUILD_ID || null

client.once('ready', async () => {
  console.log(`Discord client ready: ${client.user.tag} (${client.user.id})`)

  // Define slash commands
  const commands = [
    new SlashCommandBuilder().setName('say').setDescription('Send a message as the bot').addStringOption(opt => opt.setName('message').setDescription('Message to send').setRequired(true)).setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages),
    new SlashCommandBuilder().setName('embed').setDescription('Send an embed as the bot').addStringOption(opt => opt.setName('title').setDescription('Embed title').setRequired(true)).addStringOption(opt => opt.setName('description').setDescription('Embed description').setRequired(false)).setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages),
    new SlashCommandBuilder().setName('update').setDescription('Post an update as the bot and publish to update.html').addStringOption(opt => opt.setName('message').setDescription('Update text').setRequired(true)).setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages),
    new SlashCommandBuilder().setName('feedback').setDescription('Send feedback to the team').addStringOption(opt => opt.setName('message').setDescription('Your feedback').setRequired(true)),
    // feedback_blacklist: owners only management
    new SlashCommandBuilder().setName('feedback_blacklist').setDescription('Manage feedback blacklist (owner only)')
      .addSubcommand(sc => sc.setName('add').setDescription('Add user to feedback blacklist').addStringOption(o => o.setName('user_id').setDescription('User ID').setRequired(true)))
      .addSubcommand(sc => sc.setName('remove').setDescription('Remove user from feedback blacklist').addStringOption(o => o.setName('user_id').setDescription('User ID').setRequired(true)))
      .addSubcommand(sc => sc.setName('list').setDescription('List blacklisted user IDs')),
    new SlashCommandBuilder().setName('audit').setDescription('Run a quick service audit (env, channels, blacklist)'),
    new SlashCommandBuilder().setName('ping').setDescription('Check bot latency'),
    new SlashCommandBuilder().setName('whoami').setDescription('Show info about you'),
    new SlashCommandBuilder().setName('uptime').setDescription('Show bot uptime'),
    new SlashCommandBuilder().setName('set-log-channel').setDescription('Set runtime log channel for deploy messages').addChannelOption(o => o.setName('channel').setDescription('Target channel').setRequired(true)).setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild),
    new SlashCommandBuilder().setName('redeploy').setDescription('Run the configured redeploy command (owner only)'),
    // Message context menu: Translate
    new ContextMenuCommandBuilder().setName('Translate').setType(ApplicationCommandType.Message),
  ].map(c => c.toJSON())

  try {
    if (DEV_GUILD_ID) {
      const guild = await client.guilds.fetch(DEV_GUILD_ID)
      await guild.commands.set(commands)
      console.log('Registered commands to dev guild', DEV_GUILD_ID)
    } else {
      await client.application.commands.set(commands)
      console.log('Registered global commands')
    }
  } catch (err) {
    console.error('Failed to register slash commands:', err)
  }
  // Interaction handler for administrators/owners
  client.on('interactionCreate', async (interaction) => {
    try {
      // Handle chat input commands and message context menu
      if (interaction.isMessageContextMenuCommand && interaction.commandName === 'Translate') {
        // Translate the selected message and show a polished embed
        await interaction.deferReply({ ephemeral: true })
        const target = interaction.targetMessage
        if (!target) return interaction.editReply({ content: 'Could not access target message.' })
        const text = String(target.content || '').trim()
        if (!text) return interaction.editReply({ content: 'Message contains no text to translate.' })
        try {
          const res = await translate(text, { to: 'en' })
          const detected = res.from?.language?.iso || 'unknown'
          const original = text.length > 1900 ? text.slice(0, 1900) + '...(truncated)' : text
          const translated = String(res.text).slice(0, 1900)
          const eb = new EmbedBuilder()
            .setTitle('Translate')
            .setDescription(translated)
            .addFields(
              { name: 'Detected', value: detected, inline: true },
              { name: 'From', value: `${target.author ? `${target.author.tag}` : 'Unknown'} (${target.id})`, inline: true },
              { name: 'Original', value: original }
            )
            .setTimestamp()
            .setColor(0x1abc9c)
            .setFooter({ text: `Requested by ${interaction.user.tag}` })
          return interaction.editReply({ embeds: [eb] })
        } catch (e) {
          console.error('Translate error:', e)
          return interaction.editReply({ content: 'Translation failed.' })
        }
      }

      if (!interaction.isChatInputCommand()) return
      const name = interaction.commandName
      // Only owners may run restart
      if (name === 'redeploy') {
        if (!isOwner(interaction.user.id)) return interaction.reply({ content: 'Only owners can run redeploy.', ephemeral: true })
        const runtime = loadRuntimeConfig()
        const cmd = process.env.RESTART_CMD || runtime.restart_cmd
        await interaction.reply({ content: 'Attempting redeploy...', ephemeral: true })
        if (cmd) {
          exec(cmd, { shell: true, cwd: process.cwd(), env: process.env }, async (err, stdout, stderr) => {
            const out = String(stdout || '').slice(0, 1900)
            const errout = String(stderr || '').slice(0, 1900)
            const logId = getLogChannelId()
            try {
              const logCh = await client.channels.fetch(logId).catch(() => null)
              if (logCh) await logCh.send({ content: `Redeploy executed by ${interaction.user.tag}\n\nStdout:\n${out || '(none)'}\n\nStderr:\n${errout || '(none)'} ` })
            } catch (e) { /* ignore */ }
          })
        } else {
          // No configured restart command; exit process and rely on external supervisor
          setTimeout(() => process.exit(0), 1500)
        }
        return
      }

      if (name === 'set-log-channel') {
        if (!isOwner(interaction.user.id) && !interaction.member.permissions.has(PermissionsBitField.Flags.ManageGuild)) return interaction.reply({ content: 'Require Manage Guild or owner.', ephemeral: true })
        const ch = interaction.options.getChannel('channel')
        if (!ch) return interaction.reply({ content: 'Invalid channel', ephemeral: true })
        setLogChannelId(ch.id)
        await interaction.reply({ content: `Log channel set to ${ch.name} (${ch.id})`, ephemeral: true })
        return
      }
    } catch (e) {
      console.error('Interaction handler error:', e)
    }
  })
})

client.on('interactionCreate', async (interaction) => {
  try {
    if (!interaction.isChatInputCommand()) return

    const { commandName } = interaction

    if (commandName === 'ping') {
      const sent = await interaction.reply({ content: 'Pinging...', fetchReply: true })
      const latency = sent.createdTimestamp - interaction.createdTimestamp
      return interaction.editReply(`Pong! Websocket: ${Math.round(client.ws.ping)}ms • Roundtrip: ${latency}ms`)
    }

    if (commandName === 'whoami') {
      const u = interaction.user
      return interaction.reply({ content: `${u.tag} — ${u.id}`, ephemeral: true })
    }

    if (commandName === 'uptime') {
      const seconds = Math.floor(process.uptime())
      return interaction.reply({ content: `Uptime: ${seconds}s`, ephemeral: true })
    }

    if (commandName === 'say') {
      const msg = interaction.options.getString('message', true)
      // permission already enforced by command, but double-check
      if (!interaction.memberPermissions || !interaction.memberPermissions.has(PermissionFlagsBits.ManageMessages)) {
        return interaction.reply({ content: 'You need Manage Messages permission to use this.', ephemeral: true })
      }
      await interaction.channel.send(msg)
      return interaction.reply({ content: 'Message sent.', ephemeral: true })
    }

    if (commandName === 'embed') {
      const title = interaction.options.getString('title', true)
      const description = interaction.options.getString('description') || '\u200b'
      if (!interaction.memberPermissions || !interaction.memberPermissions.has(PermissionFlagsBits.ManageMessages)) {
        return interaction.reply({ content: 'You need Manage Messages permission to use this.', ephemeral: true })
      }
      const eb = new EmbedBuilder().setTitle(title).setDescription(description).setTimestamp().setColor(0x3498db).setFooter({ text: `Posted by ${interaction.user.tag}` })
      await interaction.channel.send({ embeds: [eb] })
      return interaction.reply({ content: 'Embed posted.', ephemeral: true })
    }

    if (commandName === 'update') {
      const msg = interaction.options.getString('message', true)
      if (!interaction.memberPermissions || !interaction.memberPermissions.has(PermissionFlagsBits.ManageMessages)) {
        return interaction.reply({ content: 'You need Manage Messages permission to use this.', ephemeral: true })
      }
      const eb = new EmbedBuilder().setDescription(msg).setTimestamp().setColor(0x3498db).setFooter({ text: `Posted by ${interaction.user.tag}` })
      await interaction.channel.send({ embeds: [eb] })
      try {
        const html = buildUpdateHtml(msg, interaction.user.tag, new Date())
        fs.writeFileSync('./update.html', html, 'utf8')
      } catch (e) {
        console.error('Failed to write update.html', e)
      }
      return interaction.reply({ content: 'Update posted and update.html saved.', ephemeral: true })
    }

    if (commandName === 'feedback') {
      const msg = interaction.options.getString('message', true)
      const blacklist = loadFeedbackBlacklist()
      if (blacklist.includes(String(interaction.user.id))) return interaction.reply({ content: 'You are not allowed to send feedback.', ephemeral: true })
      const target = await client.channels.fetch(process.env.FEEDBACK_CHANNEL_ID || FEEDBACK_CHANNEL_ID).catch(() => null)
      if (!target) return interaction.reply({ content: 'Feedback channel not available.', ephemeral: true })
      const fb = new EmbedBuilder()
        .setTitle('User Feedback')
        .addFields(
          { name: 'From', value: `${interaction.user.tag} (${interaction.user.id})`, inline: false },
          { name: 'Server', value: `${interaction.guild ? `${interaction.guild.name} (${interaction.guild.id})` : 'DM'}`, inline: true },
          { name: 'Message', value: msg.slice(0, 1900) }
        )
        .setTimestamp()
        .setColor(0x9b59b6)
      await target.send({ embeds: [fb] })
      return interaction.reply({ content: 'Thanks — your feedback has been sent.', ephemeral: true })
    }

    if (commandName === 'feedback_blacklist') {
      // owner-only subcommands: add/remove/list
      const sub = interaction.options.getSubcommand()
      if (!isOwner(interaction.user.id)) return interaction.reply({ content: 'Only bot owners can manage the feedback blacklist.', ephemeral: true })
      const list = loadFeedbackBlacklist()
      if (sub === 'add') {
        const id = interaction.options.getString('user_id', true)
        if (!list.includes(id)) list.push(id)
        saveFeedbackBlacklist(list)
        return interaction.reply({ content: `Added ${id} to feedback blacklist.`, ephemeral: true })
      }
      if (sub === 'remove') {
        const id = interaction.options.getString('user_id', true)
        const idx = list.indexOf(id)
        if (idx !== -1) list.splice(idx, 1)
        saveFeedbackBlacklist(list)
        return interaction.reply({ content: `Removed ${id} from feedback blacklist.`, ephemeral: true })
      }
      if (sub === 'list') {
        return interaction.reply({ content: `Feedback blacklist: ${list.length ? list.join(', ') : '(empty)'}`, ephemeral: true })
      }
    }

    if (commandName === 'audit') {
      // permission: owner or ManageMessages
      const memberOk = interaction.memberPermissions && interaction.memberPermissions.has(PermissionFlagsBits.ManageMessages)
      if (!isOwner(interaction.user.id) && !memberOk) return interaction.reply({ content: 'You need Manage Messages or owner access to run audit.', ephemeral: true })
      const checks = []
      const envs = ['PSYVERSE_TOKEN', 'LOG_CHANNEL', 'RENDER_WEBHOOK_SECRET', 'FEEDBACK_CHANNEL_ID']
      for (const e of envs) {
        const v = process.env[e]
        checks.push(`${e}: ${v ? 'OK' : 'MISSING'}`)
      }
      const bl = loadFeedbackBlacklist()
      checks.push(`Feedback blacklist entries: ${bl.length}`)
      try {
        const logCh = await client.channels.fetch(LOG_CHANNEL).catch(() => null)
        checks.push(`Log channel fetch: ${logCh ? 'OK' : 'FAILED'}`)
      } catch (e) {
        checks.push('Log channel fetch: ERROR')
      }
      return interaction.reply({ content: `Audit results:\n${checks.join('\n')}`, ephemeral: true })
    }
  } catch (err) {
    console.error('Interaction handler error:', err)
    try { if (interaction.replied || interaction.deferred) await interaction.editReply('An error occurred.') } catch (e) {}
  }
})
