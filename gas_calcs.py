# https://github.com/paulvha/multichannel-gas/blob/master/mics%206814.xls
from typing import Type, NewType, TypeVar

PPM = TypeVar("PPM", float, int)


class Reducing:
    @staticmethod
    def CO(reading: float) -> PPM:
        # R^2 = 0.9999
        return 4.4638 * reading ** -1.177

    @staticmethod
    def ethanol(reading: float) -> PPM:
        # R^2 = 0.9824
        return 1.363 * reading ** -1.58

    @staticmethod
    def hydrogen(reading: float) -> PPM:
        # R^2 = 0.9995
        return 0.828 * reading ** -1.781

    @staticmethod
    def ammonia(reading: float) -> PPM:
        # R^2 = 0.9967
        return 0.974 * reading ** -4.33

    @staticmethod
    def methane(reading: float) -> PPM:
        # R^2 = 0.9845
        return 837.38 * reading ** -4.093

    @staticmethod
    def propane(reading: float) -> PPM:
        # R^2 = 0.9957
        return 323.64 * reading ** -1.316

    @staticmethod
    def isobutane(reading: float) -> PPM:
        # R^2 = 0.9229
        return (-556000 * reading) + 44680

    @staticmethod
    def H2S(reading: float) -> PPM:
        # R^2 = 1.0
        return 0.0014 * reading ** -11.51


class Oxidizing:
    @staticmethod
    def hydrogen(reading: float) -> PPM:
        # R^2 = 0.9778
        return 11.109 * reading ** -10.27

    @staticmethod
    def N02(reading: float) -> PPM:
        # R^2 = 1.0
        return 0.1516 * reading ** 0.9979

    @staticmethod
    def NO(reading: float) -> PPM:
        # R^2 = 0.9982
        return 0.1011 * reading ** -6.398


class Ammonia:
    @staticmethod
    def ethanol(reading: float) -> PPM:
        # R^2 = 0.9993
        return 0.2068 * reading ** -2.781

    @staticmethod
    def hydrogen(reading: float) -> PPM:
        # R^2 = 0.9948
        return 8.0074 * reading ** -2.948

    @staticmethod
    def ammonia(reading: float) -> PPM:
        # R^2 = 0.9995
        return 0.6151 * reading ** -1.903

    @staticmethod
    def propane(reading: float) -> PPM:
        # R^2 = 0.993
        return  69.56 * reading ** -2.492

    @staticmethod
    def isobutane(reading: float) -> PPM:
        # R^2 = 0.9767
        return 503.2 * reading ** -1.888
