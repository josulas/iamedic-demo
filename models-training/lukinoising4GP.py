# Librerías

import numpy as np
import matplotlib.pyplot as plt
import cv2

# Funciones útiles para análisis de ruido

def calculate2DFT(img):
    #Cálculo de la FFT
    fft_img = np.fft.ifftshift(img)
    fft_img = np.fft.fft2(fft_img)
    fft_img = np.fft.fftshift(fft_img)
    return fft_img

def calculateMagnitudSpectrum(img):
    #FFT
    img_fft = calculate2DFT(img)
    #Magnitud Spectrum
    img_ms = 20*np.log10(np.abs(img_fft))
    return img_ms

def calculate2DInverseFT(img_fft):
    # Cálculo de la IFFT
    ift = np.fft.ifftshift(img_fft)
    ift = np.fft.ifft2(ift)
    ift = np.fft.fftshift(ift)
    ift = ift.real
    return ift


# Funciones para crear máscaras

def cr8MaskForNoise(img,thresh_list=None):
    img_ms = calculateMagnitudSpectrum(img)
    
    if thresh_list == None:
        thresh_min = np.min(img_ms)
        thresh_max = np.max(img_ms)
    else:
        thresh_min = thresh_list[0]
        thresh_max = thresh_list[1]
    
    mask = img_ms
    mask[mask<thresh_min] = 1.0
    mask[mask>thresh_max] = 1.0
    mask[mask != 1.0] = 0.0
    
    return mask

def cr8MaskForSignal(img,thresh_list=None):
    img_ms = calculateMagnitudSpectrum(img)
    
    if thresh_list == None:
        thresh_min = np.min(img_ms)
        thresh_max = np.max(img_ms)
    else:
        thresh_min = thresh_list[0]
        thresh_max = thresh_list[1]
    
    mask = img_ms
    mask[mask<thresh_min] = 0.0
    mask[mask>thresh_max] = 0.0
    mask[mask != 0.0] = 1.0
    
    return mask

# Función para denoising

def denoisingFFT(img,ths_list,mode='1'):
    
    if mode == '0':
    
        mask = cr8MaskForNoise(img,ths_list)
    
        img_fft = calculate2DFT(img)
        
        noise = calculate2DInverseFT(img_fft*mask)
        
        dummy0 = img - noise

        dummy1 = dummy0

        dummy1[dummy1 < 0] = 0

        dummy2 = np.uint8(dummy1)
        
        return dummy2
    
    elif mode == '1':
        mask = cr8MaskForSignal(img,ths_list)
        
        img_fft = calculate2DFT(img)
        
        signal = calculate2DInverseFT(img_fft*mask)
        
        signal[signal < 0] = 0
        
        signal = np.uint8(signal)
        
        return signal

# Función principal

def lukinoising(img,alpha=0.5,beta=0.5):
    
    equ = cv2.equalizeHist(img)

    img_ms = calculateMagnitudSpectrum(equ)

    umbral_inferior = np.uint16(np.mean(img_ms)+alpha*np.std(img_ms))
    umbral_superior = np.uint16(np.max(img_ms)-beta*np.std(img_ms))

    new_img = denoisingFFT(equ,[umbral_inferior,umbral_superior],mode='1')

    return new_img

# Prueba de la función
def main():
    
    path = "dataset/Set1-Training&Validation Sets CNN/Standard/25.png"
    img = cv2.imread(path,cv2.IMREAD_GRAYSCALE)
    equ = cv2.equalizeHist(img)
    new_img = lukinoising(img,alpha=0.5,beta=0.5)

    fig = plt.figure(figsize=(20,15))
    ax = fig.add_subplot(1,3,1)
    ax.imshow(img,cmap='gray')

    ax = fig.add_subplot(1,3,2)
    ax.imshow(equ,cmap='gray')

    ax = fig.add_subplot(1,3,3)
    ax.imshow(new_img,cmap='gray')

    plt.show()

if __name__ == "__main__":
    main()