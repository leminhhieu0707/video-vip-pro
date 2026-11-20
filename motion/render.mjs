// Runtime renderer for packaged apps (no webpack): node render.mjs job.json
// job = {bundle, comp, props (path to json), out, frame (null = video)}
import fs from 'node:fs';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';

const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const inputProps = JSON.parse(fs.readFileSync(job.props, 'utf8'));
const serveUrl = job.bundle;
const composition = await selectComposition({serveUrl, id: job.comp, inputProps, logLevel: 'error'});
if (job.frame !== null && job.frame !== undefined) {
  await renderStill({composition, serveUrl, output: job.out, inputProps, frame: job.frame, imageFormat: 'png', logLevel: 'error'});
} else {
  await renderMedia({composition, serveUrl, codec: 'prores', proResProfile: '4444', pixelFormat: 'yuva444p10le',
    imageFormat: 'png', muted: true, outputLocation: job.out, inputProps, logLevel: 'error'});
}
