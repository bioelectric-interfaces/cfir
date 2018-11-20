import numpy as np
import scipy.signal as sg


def get_x_chirp(fs, f0=10, f1=10):
    np.random.seed(42)
    t = np.arange(fs * 10) / fs
    amp = sg.filtfilt(*sg.butter(4, 2 / fs * 2, 'low'), np.random.randn(len(t)), method='gust')
    x = sg.chirp(t, f0=f0, f1=f1, t1=10, method='linear') * amp
    return x, np.abs(amp)


def rt_emulate(wfilter, x, chunk_size=1):
    y = [wfilter.apply(x[k:k+chunk_size]) for k in range(0, len(x), chunk_size)]
    if len(x) % chunk_size:
        y += [wfilter.apply(x[len(x) - len(x)%chunk_size:])]
    return np.concatenate(y)


def _cLS(X, Y, lambda_=0):
    """
    Complex valued Least Squares with L2 regularisation
    """
    reg = lambda_*np.eye(X.shape[1])
    b = np.dot(np.dot(np.linalg.inv(np.dot(X.T, X.conj())+reg), X.T.conj()), Y)
    return b


def _get_ideal_H(n_fft, fs, band, delay=0):
    """
    Estimate ideal delayed analytic filter freq. response
    :param n_fft: length of freq. grid
    :param fs: sampling frequency
    :param band: freq. range to apply band-pass filtering
    :param delay: delay in samples
    :return: freq. response
    """
    w = np.arange(n_fft)
    H = 2*np.exp(-2j*np.pi*w/n_fft*delay)
    H[(w/n_fft*fs<band[0]) | (w/n_fft*fs>band[1])] = 0
    return H


def cfir_win(n_taps, band, fs, delay, n_fft=2000, reg_coeff=0):
    H = _get_ideal_H(n_fft, fs, band, delay)
    F = np.array([np.exp(-2j * np.pi / n_fft * k * np.arange(n_taps)) for k in np.arange(n_fft)])
    return _cLS(F, H, reg_coeff)


class SlidingWindowFilter:
    def __init__(self, n_taps):
        self.buffer = np.zeros(n_taps)

    def apply(self, chunk):
        if len(chunk) < len(self.buffer):
            self.buffer[:-len(chunk)] = self.buffer[len(chunk):]
            self.buffer[-len(chunk):] = chunk
        else:
            self.buffer = chunk[-len(self.buffer):]
        return np.ones(len(chunk))*self.process_buffer()

    def process_buffer(self):
        raise NotImplementedError


class FiltFiltRectSWFilter(SlidingWindowFilter):
    def __init__(self, n_taps, ba_filter, ba_smoother, delay):
        super(FiltFiltRectSWFilter, self).__init__(n_taps)
        self.ba_filter = ba_filter
        self.ba_smoother = ba_smoother
        self.delay = delay

    def process_buffer(self):
        y = sg.filtfilt(*self.ba_filter, self.buffer)
        y = np.abs(y)
        y = sg.filtfilt(*self.ba_smoother, y)
        return y[-self.delay-1]


if __name__ == '__main__':
    x, amp = get_x_chirp(500)
    filt = FiltFiltRectSWFilter(1000, ([1., 0], [1]), ([1., 0], [1]), delay=0)
    np.testing.assert_allclose(np.abs(x), rt_emulate(filt, x))

    import pylab as plt
    plt.plot(rt_emulate(filt, x))
    plt.plot(np.abs(x))
    plt.show()
