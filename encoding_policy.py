"""Source-matched encoding for MP3 merges; no artificial byte budget or retry."""
LEGACY_PROFILE = 'aac-160k-stereo-44100-quicktime-v1'
PROFILE = 'aac-source-matched-quicktime-v3'
SUPPORTED_RATES = (16000, 22050, 24000, 32000, 44100, 48000)


def freeze_policy(sources):
    return {'version': PROFILE, 'selection': 'highest_verified_mp3_stream_bitrate',
            'source_bytes': sum(item['size'] for item in sources),
            'supported_rates': list(SUPPORTED_RATES)}


def choose_encoding(profiles):
    if not profiles:
        raise ValueError('Verified source audio profile evidence is missing')
    rates = {int(profile[1]) for profile in profiles}
    channels = {profile[2] for profile in profiles}
    if len(rates)>1:
        raise ValueError('These audio files use different sample rates. This book needs an encoding review before it can be joined.')
    if not rates.issubset(SUPPORTED_RATES):
        raise ValueError('Selected source sample rates differ or are unsupported; an encoding decision is needed before retrying.')
    if len(channels) > 1:
        raise ValueError('These audio files mix mono and stereo recordings. This book needs an encoding review before it can be joined.')
    if not channels.issubset({1, 2}):
        raise ValueError('This audio recording has more than two channels. This book needs an encoding review before conversion.')
    if any(profile[0] != 'mp3' for profile in profiles):
        raise ValueError('Source-matched AAC selection currently supports MP3 recordings; this source format needs an encoding review.')
    bitrates = []
    for profile in profiles:
        value = profile[3]
        if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isdigit() or not 8000 <= int(value) <= 320000:
            raise ValueError('The app cannot determine suitable audio settings from these source files. This book needs an encoding review before conversion.')
        bitrates.append(int(value))
    rate = next(iter(rates)); channel = next(iter(channels)); target = max(bitrates)
    # Fail rather than let AAC silently clamp a source target above frame capacity.
    if target > 6 * rate * channel:
        raise ValueError('The verified source bitrate exceeds this AAC profile capacity; an encoding decision is needed before retrying.')
    return {'bitrate': target, 'channels': channel, 'sample_rate': rate,
            'source_bitrates': bitrates, 'selection': 'highest_verified_mp3_stream_bitrate'}
