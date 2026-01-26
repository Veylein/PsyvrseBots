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
import { Client, GatewayIntentBits, EmbedBuilder, PermissionsBitField } from 'discord.js'

dotenv.config()

const {
  PSYVERSE_TOKEN,
  LOG_CHANNEL,
  RENDER_WEBHOOK_SECRET,
  RENDER_API_KEY,
  PORT = 3000,
  FAILURE_ROLE_ID,
  SILENCE_SUCCESS = 'false',
} = process.env

const SILENCE_OK = String(SILENCE_SUCCESS).toLowerCase() === 'true'

// Validate important environment variables early to fail fast with clear messages
function isPlaceholder(value) {
  if (!value) return true
  const s = String(value).toLowerCase()
  return /your_|example|replace|xxx|changeme/.test(s)
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

    if (cmd === 'feedback') {
      if (!args) return message.reply('Usage: $feedback <your message>')
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

    // Send to channel
    if (!LOG_CHANNEL) {
      console.error('LOG_CHANNEL not set; cannot post message')
      return res.status(500).send('Discord channel not configured')
    }

    const channel = await client.channels.fetch(LOG_CHANNEL).catch(e => null)
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
import { SlashCommandBuilder, PermissionFlagsBits } from 'discord.js'

const DEV_GUILD_ID = process.env.DEV_GUILD_ID || null

client.once('ready', async () => {
  console.log(`Discord client ready: ${client.user.tag} (${client.user.id})`)

  // Define slash commands
  const commands = [
    new SlashCommandBuilder().setName('say').setDescription('Send a message as the bot').addStringOption(opt => opt.setName('message').setDescription('Message to send').setRequired(true)).setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages),
    new SlashCommandBuilder().setName('embed').setDescription('Send an embed as the bot').addStringOption(opt => opt.setName('title').setDescription('Embed title').setRequired(true)).addStringOption(opt => opt.setName('description').setDescription('Embed description').setRequired(false)).setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages),
    new SlashCommandBuilder().setName('feedback').setDescription('Send feedback to the team').addStringOption(opt => opt.setName('message').setDescription('Your feedback').setRequired(true)),
    new SlashCommandBuilder().setName('ping').setDescription('Check bot latency'),
    new SlashCommandBuilder().setName('whoami').setDescription('Show info about you'),
    new SlashCommandBuilder().setName('uptime').setDescription('Show bot uptime'),
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

    if (commandName === 'feedback') {
      const msg = interaction.options.getString('message', true)
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
  } catch (err) {
    console.error('Interaction handler error:', err)
    try { if (interaction.replied || interaction.deferred) await interaction.editReply('An error occurred.') } catch (e) {}
  }
})
