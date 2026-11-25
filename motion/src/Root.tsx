import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Base, BlueBig, BlueText, Checklist, FollowCard, NumberTitle, ScreenCard, Tiles} from './blue/Blue';
import {VIP_COMPS} from './blue/Vip';
import {PRO_COMPS} from './blue/Pro';
import {TREND_COMPS} from './blue/Trend';
import {TEXT_COMPS} from './blue/Text';
import {HUD_COMPS} from './blue/Hud';
import {ESTATE_COMPS} from './blue/Estate';

const FPS = 30;

// Duration, size and fps come from the props render_motion.py passes, so one composition serves any clip length.
const meta: CalculateMetadataFunction<Base & {fps?: number}> = async ({props}) => ({
  durationInFrames: Math.max(1, Math.round((props.duration || 3) * (props.fps || FPS))),
  fps: props.fps || FPS,
  width: props.width || 1080,
  height: props.height || 1920,
  defaultCodec: 'prores',
  defaultVideoImageFormat: 'png',
  defaultPixelFormat: 'yuva444p10le',
  defaultProResProfile: '4444',
});

const common = {durationInFrames: 90, fps: FPS, width: 1080, height: 1920, calculateMetadata: meta};

export const Root: React.FC = () => (
  <>
    <Composition id="BlueText" component={BlueText as React.FC<any>} {...common}
      defaultProps={{duration: 3}} />
    <Composition id="BlueBig" component={BlueBig as React.FC<any>} {...common}
      defaultProps={{duration: 3}} />
    <Composition id="Tiles" component={Tiles as React.FC<any>} {...common}
      defaultProps={{duration: 3}} />
    <Composition id="Checklist" component={Checklist as React.FC<any>} {...common}
      defaultProps={{duration: 3}} />
    <Composition id="ScreenCard" component={ScreenCard as React.FC<any>} {...common}
      defaultProps={{duration: 3}} />
    <Composition id="NumberTitle" component={NumberTitle as React.FC<any>} {...common}
      defaultProps={{duration: 3}} />
    <Composition id="FollowCard" component={FollowCard as React.FC<any>} {...common}
      defaultProps={{duration: 3}} />
    {Object.entries({...VIP_COMPS, ...PRO_COMPS, ...TREND_COMPS, ...TEXT_COMPS, ...HUD_COMPS, ...ESTATE_COMPS}).map(([id, comp]) => (
      <Composition key={id} id={id} component={comp} {...common} defaultProps={{duration: 3}} />
    ))}
  </>
);
