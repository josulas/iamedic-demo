import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import cv2
from typing import Self, Tuple, List
from scipy.ndimage import label

def fit_ellipse(thresh: np.ndarray):
    """
    Fits an ellipse to the largest contour in a binary image.

    :param thresh: Binary image (numpy array) where the ellipse will be fitted.
    :return: An Ellipse object representing the fitted ellipse.
    """
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(contours, key=cv2.contourArea)  # si hay varios, elige el más grande

    # 4) Ajusta una elipse al contorno
    ellipse = cv2.fitEllipse(cnt)
    (center, axes, angle) = ellipse
    (eje_mayor, eje_menor) = axes  # axes = (longitud_eje_mayor, longitud_eje_menor)

    print(f"Eje mayor   ≈ {eje_mayor:.1f} px")
    print(f"Eje menor   ≈ {eje_menor:.1f} px")  # este es el ANCHO de la NT

    # 5) (Opcional) convierte a mm si conoces la escala
    pixel_mm = 1 / 0.05  # mm por píxel, ej.
    print(f"Ancho NT ≈ {eje_menor * pixel_mm:.2f} mm")
    # 6) Grafica

    ellipse_patch = Ellipse(xy=center,
                            width=eje_mayor,
                            height=eje_menor,
                            angle=angle,
                            linestyle='-',
                            edgecolor='cyan',
                            fill=False)
    return ellipse_patch


def plot_with_ellipse(self, ellipse_patch: Ellipse, c: float = 0.1719077568134172) -> None:
    """
    Plots the image alongside a fitted ellipse

    arg c: float indicating pixel resolution in [px/mm]
    """

    center = ellipse_patch.center
    R_min, R_max = ellipse_patch.height / 2, ellipse_patch.width / 2
    angle = np.pi * ellipse_patch.angle / 180
    offset_point = np.array([-R_min * np.sin(angle), R_min * np.cos(angle)])
    TN_topmark = np.floor(center + offset_point)
    TN_botmark = np.floor(center - offset_point)
    TN_meas = np.linalg.norm(TN_topmark - TN_botmark)
    #
    fig, ax = plt.subplots()  # figsize=(10, 10))
    ax.imshow(self, vmin=0, vmax=255, cmap='gray')
    ax.add_patch(ellipse_patch)
    ax.plot(center[0], center[1], 'ro', markersize=1)
    ax.plot([TN_topmark[0], TN_botmark[0]], [TN_topmark[1], TN_botmark[1]],
            linestyle='--',
            color='y',
            marker='+',
            markersize=6,
            linewidth=0.5,
            label=f"TN={TN_meas / c:.2f} [mm]")

    plt.legend(loc='upper left', fontsize='big', prop={'weight': 'bold'})
    plt.axis('off')
    plt.show()

    return TN_meas / c  # return TN in [mm] as a float


# %%

for i in range(100):
    original_image = cv2.imread(f'../preprocessed_images/{i}.png', cv2.IMREAD_GRAYSCALE)
    image_mask = cv2.imread(f'../segmentations/seg_{i}.png', cv2.IMREAD_GRAYSCALE)
    # plot elipse return value
    ellipse_patch = fit_ellipse(image_mask)
    tn_meas = plot_with_ellipse(original_image, ellipse_patch)
    print(f'TN measurement: {tn_meas:.2f} mm')

