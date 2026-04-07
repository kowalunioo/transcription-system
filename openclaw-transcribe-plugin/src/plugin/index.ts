import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);

const schema = {
  type: 'object',
  additionalProperties: false,
  required: ['path'],
  properties: {
    path: { type: 'string', description: 'Local path to media file or a YouTube URL when source="youtube".' },
    source: { type: 'string', enum: ['file', 'youtube'] },
    tier: { type: 'string', enum: ['free', 'dev'] },
    language: { anyOf: [{ type: 'string' }, { type: 'null' }] },
    output_format: { type: 'string', enum: ['text', 'json', 'srt', 'all'] },
    timestamps: { type: 'boolean' },
    diarization: { type: 'boolean' },
    task: { type: 'string', enum: ['transcribe', 'translate'] },
    model: { type: 'string' },
    word_timestamps: { type: 'boolean' },
    chunk_overlap_seconds: { type: 'number' }
  }
};

function summarizePayload(payload: Record<string, unknown>) {
  const transcription = payload.transcription && typeof payload.transcription === 'object' ? payload.transcription as Record<string, unknown> : null;
  const text = typeof transcription?.text === 'string' ? transcription.text : '';
  const segments = Array.isArray(transcription?.segments) ? transcription?.segments as unknown[] : [];
  const artifacts = transcription?.artifacts && typeof transcription.artifacts === 'object' ? transcription.artifacts as Record<string, unknown> : {};
  const source = typeof payload.source === 'string' ? payload.source : 'file';
  const chunked = Boolean(payload.chunked ?? transcription?.chunked);
  const selectedInputPath = typeof payload.selected_input_path === 'string' ? payload.selected_input_path : undefined;
  const aggregateArtifacts = payload.aggregate_artifacts && typeof payload.aggregate_artifacts === 'object' ? payload.aggregate_artifacts as Record<string, unknown> : undefined;

  return {
    ok: Boolean(payload.ok),
    source,
    chunked,
    text,
    segment_count: segments.length,
    selected_input_path: selectedInputPath,
    artifacts,
    aggregate_artifacts: aggregateArtifacts,
  };
}

function jsonResult(payload: Record<string, unknown>) {
  const summary = summarizePayload(payload);
  return {
    content: [{ type: 'text', text: JSON.stringify(summary, null, 2) }],
    details: payload,
  };
}

export default {
  id: 'openclaw-transcribe',
  name: 'OpenClaw Transcribe',
  description: 'Local media/YouTube transcription tool wrapper with preprocessing and chunked Groq pipeline',
  configSchema: {
    parse(value: unknown) {
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    },
  },
  register(api: OpenClawPluginApi) {
    api.registerTool(() => ({
      name: 'transcribe_media',
      label: 'Transcribe Media',
      description: 'Transcribe local audio/video files or YouTube URLs through the full preprocessing + chunking pipeline. Returns transcript text, chunking metadata, and artifact paths.',
      parameters: schema,
      async execute(_toolCallId, params) {
        const p = params as Record<string, unknown>;
        const pluginConfig = (api.pluginConfig && typeof api.pluginConfig === 'object' && !Array.isArray(api.pluginConfig)) ? api.pluginConfig as Record<string, unknown> : {};
        const pluginDir = dirname(fileURLToPath(import.meta.url));
        const root = resolve(pluginDir, '../../..');
        const scriptPath = typeof pluginConfig.scriptPath === 'string' ? pluginConfig.scriptPath : resolve(root, 'bin/transcribe-media-pipeline');
        const args: string[] = [String(p.path ?? '')];
        const outputFormat = typeof p.output_format === 'string' ? p.output_format : (typeof pluginConfig.defaultOutputFormat === 'string' ? pluginConfig.defaultOutputFormat : 'json');
        const timestamps = typeof p.timestamps === 'boolean' ? p.timestamps : Boolean(pluginConfig.defaultTimestamps ?? true);
        const diarization = typeof p.diarization === 'boolean' ? p.diarization : false;
        const wordTimestamps = typeof p.word_timestamps === 'boolean' ? p.word_timestamps : false;
        const language = typeof p.language === 'string' ? p.language : (pluginConfig.defaultLanguage === null ? null : (typeof pluginConfig.defaultLanguage === 'string' ? pluginConfig.defaultLanguage : null));
        const source = typeof p.source === 'string' ? p.source : (typeof pluginConfig.defaultSource === 'string' ? pluginConfig.defaultSource : 'file');
        const tier = typeof p.tier === 'string' ? p.tier : (typeof pluginConfig.defaultTier === 'string' ? pluginConfig.defaultTier : 'free');
        const chunkOverlapSeconds = typeof p.chunk_overlap_seconds === 'number'
          ? p.chunk_overlap_seconds
          : (typeof pluginConfig.chunkOverlapSeconds === 'number' ? pluginConfig.chunkOverlapSeconds : undefined);
        args.push('--source', source, '--tier', tier, '--output-format', outputFormat);
        if (timestamps) args.push('--timestamps');
        if (language) args.push('--language', language);
        if (typeof chunkOverlapSeconds === 'number' && Number.isFinite(chunkOverlapSeconds) && chunkOverlapSeconds >= 0) {
          args.push('--chunk-overlap-seconds', String(Math.floor(chunkOverlapSeconds)));
        }
        if (diarization || wordTimestamps || p.task || p.model || typeof pluginConfig.outputDir === 'string' || typeof pluginConfig.tempDir === 'string') {
          // Accepted for interface compatibility, but currently handled by the backend/transcribe wrapper rather than the pipeline entrypoint.
        }
        try {
          const { stdout, stderr } = await execFileAsync(scriptPath, args, { cwd: root, maxBuffer: 20 * 1024 * 1024, env: process.env });
          const payload = JSON.parse(stdout) as Record<string, unknown>;
          if (stderr?.trim()) payload.stderr = stderr.trim();
          return jsonResult(payload);
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          const stdout = typeof error === 'object' && error && 'stdout' in error ? String((error as any).stdout ?? '') : '';
          const stderr = typeof error === 'object' && error && 'stderr' in error ? String((error as any).stderr ?? '') : '';
          return jsonResult({ ok: false, error: message, stdout, stderr, scriptPath, args });
        }
      },
    }));
  },
};
