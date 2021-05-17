import pandas as pd


def up_filter(df: pd.DataFrame, andon_flag='andon', up_filter_size='15s'):
    
    df = df.copy()
    if up_filter_size == '0s':
        df[f'{andon_flag}_up_filtered'] = df[andon_flag]
        return df

    df[f'{andon_flag}_up_filtered'] = df[andon_flag]
    df['andon_change'] = df[andon_flag].diff()

    up_starts = df.loc[df['andon_change'] == 1].index
    down_starts = df.loc[df['andon_change'] == -1.0].index

    if not down_starts.empty:
        down_starts = [ds for ds in down_starts if ds > up_starts[0]]
    if len(up_starts) > len(down_starts):
        up_starts = up_starts[:len(down_starts)]

    for us, ds in zip(up_starts, down_starts):
        if ds - us < pd.to_timedelta(up_filter_size):
            df.loc[us:ds, f'{andon_flag}_up_filtered'] = 0

    return df


def down_filter(df: pd.DataFrame, andon_flag='andon', down_filter_size='15s'):
    
    df = df.copy()
    if down_filter_size == '0s':
        df[f'{andon_flag}_down_filtered'] = df[andon_flag]
        return df

    df[f'{andon_flag}_down_filtered'] = df[andon_flag]
    df['andon_change'] = df[andon_flag].diff()

    up_starts = df.loc[df['andon_change'] == 1.0].index
    down_starts = df.loc[df['andon_change'] == -1.0].index

    if not down_starts.empty:
        up_starts = [us for us in up_starts if us > down_starts[0]]
    if len(down_starts) > len(up_starts):
        down_starts = down_starts[:len(up_starts)]

    for ds, us in zip(down_starts, up_starts):
        if us - ds < pd.to_timedelta(down_filter_size):
            df.loc[ds:us, f'{andon_flag}_down_filtered'] = 1

    return df


def filtering(df: pd.DataFrame, andon_flag='andon', up_filter_size='15s', down_filter_size='10s', first_filter='down'):
    df = df.copy()
    if first_filter == 'down':
        df = down_filter(df, andon_flag=andon_flag, down_filter_size=down_filter_size)
        df = up_filter(df, andon_flag=f'{andon_flag}_down_filtered', up_filter_size=up_filter_size)
        df[f'{andon_flag}_filtered'] = df[f'{andon_flag}_down_filtered_up_filtered']
    elif first_filter == 'up':
        df = up_filter(df, andon_flag=andon_flag, up_filter_size=up_filter_size)
        df = down_filter(df, andon_flag=f'{andon_flag}_up_filtered', down_filter_size=down_filter_size)
        df[f'{andon_flag}_filtered'] = df[f'{andon_flag}_up_filtered_down_filtered']

    return df