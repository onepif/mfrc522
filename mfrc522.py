#!/usr/bin/env python
# -*- coding: utf8 -*-
#
#   Copyright 2014,2018 Mario Gomez <mario.gomez@teubi.co>
#
#   This file is part of MFRC522-Python
#   MFRC522-Python is a simple Python implementation for
#   the MFRC522 NFC Card Reader for the Raspberry Pi
#
#   MFRC522-Python is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Lesser General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version
#
#   MFRC522-Python is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Lesser General Public License for more details
#
#   You should have received a copy of the GNU Lesser General Public License
#   along with MFRC522-Python.  If not, see <http:#www.gnu.org/licenses/>

import RPi.GPIO as GPIO
import spidev, logging, sys
from time import sleep

class MFRC522:
	README="""Class to use w/ RFID MODULE KIT 13.56 MHZ

There are three hardware components involved:
1) The micro computer: raspbery pi
2) The PCD (short for Proximity Coupling Device): RFID MFRC522 Contactless Reader IC
3) The PICC (short for Proximity Integrated Circuit Card): A card or tag using the ISO 14443A interface, eg Mifare or NTAG203

The microcontroller and card reader uses SPI for communication
The protocol is described in the MFRC522 datasheet: http:#www.nxp.com/documents/data_sheet/MFRC522.pdf

The card reader and the tags communicate using a 13.56MHz electromagnetic field
The protocol is defined in ISO/IEC 14443-3 Identification cards -- Contactless integrated circuit cards -- Proximity cards -- Part 3: Initialization and anticollision"
A free version of the final draft can be found at http:#wg8.de/wg8n1496_17n3613_Ballot_FCD14443-3.pdf
Details are found in chapter 6, Type A – Initialization and anticollision

Схема подключения (Распиновка)
----------------------------------------------------------------------------------
Контакт MFRC522 	Контакт Raspberry Pi (Physical Pin)		Назначение
----------------------------------------------------------------------------------
	VCC					Pin 1 (3.3V)						Питание (строго 3.3В!)
	RST					Pin 22 (GPIO 25)					Сброс (Reset)
	GND					Pin 6 (GND)							Земля
	MISO				Pin 21 (GPIO 9)						Master In Slave Out
	MOSI				Pin 19 (GPIO 10)					Master Out Slave In
	SCK					Pin 23 (GPIO 11)					Serial Clock
	SDA (SS)			Pin 24 (GPIO 8)						Chip Select

на самой raspbery надо установить:
----------------------------------------------------------------------------------
pip3 install --break-system-packages spidev
----------------------------------------------------------------------------------

инициализация:
----------------------------------------------------------------------------------
python
import mfrc522
m = mfrc522.MFRC522(0,0,1000000,10,-1,20)

выполнение:
----------------------------------------------------------------------------------
m.dump()
m.read()
m.test()
m.write()
----------------------------------------------------------------------------------

If only the PICC UID is wanted, the above documents has all the needed information
To read and write from MIFARE PICCs, the MIFARE protocol is used after the PICC has been selected
The MIFARE Classic chips and protocol is described in the datasheets:
		1K:   http:#www.nxp.com/documents/data_sheet/MF1S503x.pdf
		4K:   http:#www.nxp.com/documents/data_sheet/MF1S703x.pdf
		Mini: http:#www.idcardmarket.com/download/mifare_S20_datasheet.pdf
The MIFARE Ultralight chip and protocol is described in the datasheets:
		Ultralight:   http:#www.nxp.com/documents/data_sheet/MF0ICU1.pdf
		Ultralight C: http:#www.nxp.com/documents/short_data_sheet/MF0ICU2_SDS.pdf

MIFARE Classic 1K (MF1S503x):
		Has 16 sectors * 4 blocks/sector * 16 bytes/block = 1024 bytes
		The blocks are numbered 0-63
		Block 3 in each sector is the Sector Trailer. See http:#www.nxp.com/documents/data_sheet/MF1S503x.pdf sections 8.6 and 8.7:
				Bytes 0-5:   Key A
				Bytes 6-8:   Access Bits
				Bytes 9:	 User data
				Bytes 10-15: Key B (or user data)
		Block 0 is read-only manufacturer data
		To access a block, an authentication using a key from the block's sector must be performed first
		Example: To read from block 10, first authenticate using a key from sector 3 (blocks 8-11)
		All keys are set to FFFFFFFFFFFFh at chip delivery
		Warning: Please read section 8.7 "Memory Access". It includes this text: if the PICC detects a format violation the whole sector is irreversibly blocked
		To use a block in "value block" mode (for Increment/Decrement operations) you need to change the sector trailer. Use PICC_SetAccessBits() to calculate the bit patterns
MIFARE Classic 4K (MF1S703x):
		Has (32 sectors * 4 blocks/sector + 8 sectors * 16 blocks/sector) * 16 bytes/block = 4096 bytes
		The blocks are numbered 0-255
		The last block in each sector is the Sector Trailer like above
MIFARE Classic Mini (MF1 IC S20):
		Has 5 sectors * 4 blocks/sector * 16 bytes/block = 320 bytes
		The blocks are numbered 0-19
		The last block in each sector is the Sector Trailer like above

MIFARE Ultralight (MF0ICU1):
		Has 16 pages of 4 bytes = 64 bytes
		Pages 0 + 1 is used for the 7-byte UID
		Page 2 contains the last chech digit for the UID, one byte manufacturer internal data, and the lock bytes (see http:#www.nxp.com/documents/data_sheet/MF0ICU1.pdf section 8.5.2)
		Page 3 is OTP, One Time Programmable bits. Once set to 1 they cannot revert to 0
		Pages 4-15 are read/write unless blocked by the lock bytes in page 2. 
MIFARE Ultralight C (MF0ICU2):
		Has 48 pages of 4 bytes = 64 bytes
		Pages 0 + 1 is used for the 7-byte UID
		Page 2 contains the last chech digit for the UID, one byte manufacturer internal data, and the lock bytes (see http:#www.nxp.com/documents/data_sheet/MF0ICU1.pdf section 8.5.2)
		Page 3 is OTP, One Time Programmable bits. Once set to 1 they cannot revert to 0
		Pages 4-39 are read/write unless blocked by the lock bytes in page 2. 
		Page 40 Lock bytes
		Page 41 16 bit one way counter
		Pages 42-43 Authentication configuration
		Pages 44-47 Authentication key"""

	# Firmware data for self-test
	# Reference values based on firmware version; taken from 16.1.1 in spec
	# Version 1.0
	MFRC522_firmware_referenceV1_0 = [
		0x00, 0xC6, 0x37, 0xD5, 0x32, 0xB7, 0x57, 0x5C,
		0xC2, 0xD8, 0x7C, 0x4D, 0xD9, 0x70, 0xC7, 0x73,
		0x10, 0xE6, 0xD2, 0xAA, 0x5E, 0xA1, 0x3E, 0x5A,
		0x14, 0xAF, 0x30, 0x61, 0xC9, 0x70, 0xDB, 0x2E,
		0x64, 0x22, 0x72, 0xB5, 0xBD, 0x65, 0xF4, 0xEC,
		0x22, 0xBC, 0xD3, 0x72, 0x35, 0xCD, 0xAA, 0x41,
		0x1F, 0xA7, 0xF3, 0x53, 0x14, 0xDE, 0x7E, 0x02,
		0xD9, 0x0F, 0xB5, 0x5E, 0x25, 0x1D, 0x29, 0x79
	]
	# Version 2.0
	MFRC522_firmware_referenceV2_0 = [
		0x00, 0xEB, 0x66, 0xBA, 0x57, 0xBF, 0x23, 0x95,
		0xD0, 0xE3, 0x0D, 0x3D, 0x27, 0x89, 0x5C, 0xDE,
		0x9D, 0x3B, 0xA7, 0x00, 0x21, 0x5B, 0x89, 0x82,
		0x51, 0x3A, 0xEB, 0x02, 0x0C, 0xA5, 0x00, 0x49,
		0x7C, 0x84, 0x4D, 0xB3, 0xCC, 0xD2, 0x1B, 0x81,
		0x5D, 0x48, 0x76, 0xD5, 0x71, 0x61, 0x21, 0xA9,
		0x86, 0x96, 0x83, 0x38, 0xCF, 0x9D, 0x5B, 0x6D,
		0xDC, 0x15, 0xBA, 0x3E, 0x7D, 0x95, 0x3B, 0x2F
	]

	# MFRC522 registers. Described in chapter 9 of the datasheet
	# When using SPI all addresses are shifted one bit left in the "SPI address byte" (section 8.1.2.3)
	# PCD_Register
	# Page 0: Command and status
	#						  0x00			# reserved for future use
	CommandReg				= 0x01 << 1		# starts and stops command execution
	ComIEnReg				= 0x02 << 1		# enable and disable interrupt request control bits
	DivIEnReg				= 0x03 << 1		# enable and disable interrupt request control bits
	ComIrqReg				= 0x04 << 1		# interrupt request bits
	DivIrqReg				= 0x05 << 1		# interrupt request bits
	ErrorReg				= 0x06 << 1		# error bits showing the error status of the last command executed 
	Status1Reg				= 0x07 << 1		# communication status bits
	Status2Reg				= 0x08 << 1		# receiver and transmitter status bits
	FIFODataReg				= 0x09 << 1		# input and output of 64 byte FIFO buffer
	FIFOLevelReg			= 0x0A << 1		# number of bytes stored in the FIFO buffer
	WaterLevelReg			= 0x0B << 1		# level for FIFO underflow and overflow warning
	ControlReg				= 0x0C << 1		# miscellaneous control registers
	BitFramingReg			= 0x0D << 1		# adjustments for bit-oriented frames
	CollReg					= 0x0E << 1		# bit position of the first bit-collision detected on the RF interface
	#						  0x0F			# reserved for future use

	# Page 1: Command
	# 						  0x10			# reserved for future use
	ModeReg					= 0x11 << 1		# defines general modes for transmitting and receiving 
	TxModeReg				= 0x12 << 1		# defines transmission data rate and framing
	RxModeReg				= 0x13 << 1		# defines reception data rate and framing
	TxControlReg			= 0x14 << 1		# controls the logical behavior of the antenna driver pins TX1 and TX2
	TxASKReg				= 0x15 << 1		# controls the setting of the transmission modulation
	TxSelReg				= 0x16 << 1		# selects the internal sources for the antenna driver
	RxSelReg				= 0x17 << 1		# selects internal receiver settings
	RxThresholdReg			= 0x18 << 1		# selects thresholds for the bit decoder
	DemodReg				= 0x19 << 1		# defines demodulator settings
	# 						  0x1A			# reserved for future use
	# 						  0x1B			# reserved for future use
	MfTxReg					= 0x1C << 1		# controls some MIFARE communication transmit parameters
	MfRxReg					= 0x1D << 1		# controls some MIFARE communication receive parameters
	# 						  0x1E			# reserved for future use
	SerialSpeedReg			= 0x1F << 1		# selects the speed of the serial UART interface

	# Page 2: Configuration
	# 						  0x20			# reserved for future use
	CRCResultRegH			= 0x21 << 1		# shows the MSB and LSB values of the CRC calculation
	CRCResultRegL			= 0x22 << 1
	# 						  0x23			# reserved for future use
	ModWidthReg				= 0x24 << 1		# controls the ModWidth setting?
	# 						  0x25			# reserved for future use
	RFCfgReg				= 0x26 << 1		# configures the receiver gain
	GsNReg					= 0x27 << 1		# selects the conductance of the antenna driver pins TX1 and TX2 for modulation 
	CWGsPReg				= 0x28 << 1		# defines the conductance of the p-driver output during periods of no modulation
	ModGsPReg				= 0x29 << 1		# defines the conductance of the p-driver output during periods of modulation
	TModeReg				= 0x2A << 1		# defines settings for the internal timer
	TPrescalerReg			= 0x2B << 1		# the lower 8 bits of the TPrescaler value. The 4 high bits are in TModeReg
	TReloadRegH				= 0x2C << 1		# defines the 16-bit timer reload value
	TReloadRegL				= 0x2D << 1
	TCounterValueRegH		= 0x2E << 1		# shows the 16-bit timer value
	TCounterValueRegL		= 0x2F << 1

	# Page 3: Test Registers
	# 						  0x30			# reserved for future use
	TestSel1Reg				= 0x31 << 1		# general test signal configuration
	TestSel2Reg				= 0x32 << 1		# general test signal configuration
	TestPinEnReg			= 0x33 << 1		# enables pin output driver on pins D1 to D7
	TestPinValueReg			= 0x34 << 1		# defines the values for D1 to D7 when it is used as an I/O bus
	TestBusReg				= 0x35 << 1		# shows the status of the internal test bus
	AutoTestReg				= 0x36 << 1		# controls the digital self test
	VersionReg				= 0x37 << 1		# shows the software version
	AnalogTestReg			= 0x38 << 1		# controls the pins AUX1 and AUX2
	TestDAC1Reg				= 0x39 << 1		# defines the test value for TestDAC1
	TestDAC2Reg				= 0x3A << 1		# defines the test value for TestDAC2
	TestADCReg				= 0x3B << 1		# shows the value of ADC I and Q channels
	# 						  0x3C			# reserved for production tests
	# 						  0x3D			# reserved for production tests
	# 						  0x3E			# reserved for production tests
	# 						  0x3F			# reserved for production tests

	# MFRC522 commands. Described in chapter 10 of the datasheet
	# PCD_Command
	PCD_Idle				= 0x00			# no action, cancels current command execution
	PCD_Mem					= 0x01			# stores 25 bytes into the internal buffer
	PCD_GenerateRandomID	= 0x02			# generates a 10-byte random ID number
	PCD_CalcCRC				= 0x03			# activates the CRC coprocessor or performs a self test
	PCD_Transmit			= 0x04			# transmits data from the FIFO buffer
	PCD_NoCmdChange			= 0x07			# no command change, can be used to modify the CommandReg register bits without affecting the command, for example, the PowerDown bit
	PCD_Receive				= 0x08			# activates the receiver circuits
	PCD_Transceive 			= 0x0C			# transmits data from FIFO buffer to antenna and automatically activates the receiver after transmission
	PCD_MFAuthent 			= 0x0E			# performs the MIFARE standard authentication as a reader
	PCD_SoftReset			= 0x0F			# resets the MFRC522

	# MFRC522 RxGain[2:0] masks, defines the receiver's signal voltage gain factor (on the PCD)
	# Described in 9.3.3.6 / table 98 of the datasheet at http:#www.nxp.com/documents/data_sheet/MFRC522.pdf
	# PCD_RxGain
	RxGain_18dB				= 0x00 << 4		# 000b - 18 dB, minimum
	RxGain_23dB				= 0x01 << 4		# 001b - 23 dB
	RxGain_18dB_2			= 0x02 << 4		# 010b - 18 dB, it seems 010b is a duplicate for 000b
	RxGain_23dB_2			= 0x03 << 4		# 011b - 23 dB, it seems 011b is a duplicate for 001b
	RxGain_33dB				= 0x04 << 4		# 100b - 33 dB, average, and typical default
	RxGain_38dB				= 0x05 << 4		# 101b - 38 dB
	RxGain_43dB				= 0x06 << 4		# 110b - 43 dB
	RxGain_48dB				= 0x07 << 4		# 111b - 48 dB, maximum
	RxGain_min				= 0x00 << 4		# 000b - 18 dB, minimum, convenience for RxGain_18dB
	RxGain_avg				= 0x04 << 4		# 100b - 33 dB, average, convenience for RxGain_33dB
	RxGain_max				= 0x07 << 4		# 111b - 48 dB, maximum, convenience for RxGain_48dB

	# Commands sent to the PICC
	# PICC_Command
	# The commands used by the PCD to manage communication with several PICCs (ISO 14443-3, Type A, section 6.4)
	PICC_CMD_REQA			= 0x26			# REQuest command, Type A. Invites PICCs in state IDLE to go to READY and prepare for anticollision or selection. 7 bit frame
	PICC_CMD_WUPA			= 0x52			# Wake-UP command, Type A. Invites PICCs in state IDLE and HALT to go to READY(*) and prepare for anticollision or selection. 7 bit frame
	PICC_CMD_CT				= 0x88			# Cascade Tag. Not really a command, but used during anti collision
	PICC_CMD_SEL_CL1		= 0x93			# Anti collision/Select, Cascade Level 1
	PICC_CMD_SEL_CL2		= 0x95			# Anti collision/Select, Cascade Level 2
	PICC_CMD_SEL_CL3		= 0x97			# Anti collision/Select, Cascade Level 3
	PICC_CMD_HLTA			= 0x50			# HaLT command, Type A. Instructs an ACTIVE PICC to go to state HALT
	# The commands used for MIFARE Classic (from http:#www.nxp.com/documents/data_sheet/MF1S503x.pdf, Section 9)
	# Use PCD_MFAuthent to authenticate access to a sector, then use these commands to read/write/modify the blocks on the sector
	# The read/write commands can also be used for MIFARE Ultralight
	PICC_CMD_MF_AUTH_KEY_A	= 0x60			# Perform authentication with Key A
	PICC_CMD_MF_AUTH_KEY_B	= 0x61			# Perform authentication with Key B
	PICC_CMD_MF_READ		= 0x30			# Reads one 16 byte block from the authenticated sector of the PICC. Also used for MIFARE Ultralight
	PICC_CMD_MF_WRITE		= 0xA0			# Writes one 16 byte block to the authenticated sector of the PICC. Called "COMPATIBILITY WRITE" for MIFARE Ultralight
	PICC_CMD_MF_DECREMENT	= 0xC0			# Decrements the contents of a block and stores the result in the internal data register
	PICC_CMD_MF_INCREMENT	= 0xC1			# Increments the contents of a block and stores the result in the internal data register
	PICC_CMD_MF_RESTORE		= 0xC2			# Reads the contents of a block into the internal data register
	PICC_CMD_MF_TRANSFER	= 0xB0			# Writes the contents of the internal data register to a block
	# The commands used for MIFARE Ultralight (from http:#www.nxp.com/documents/data_sheet/MF0ICU1.pdf, Section 8.6)
	# The PICC_CMD_MF_READ and PICC_CMD_MF_WRITE can also be used for MIFARE Ultralight
	PICC_CMD_UL_WRITE		= 0xA2			# Writes one 4 byte page to the PICC

	# MIFARE constants that does not fit anywhere else
	# MIFARE_Misc
	MF_ACK					= 0xA			# The MIFARE Classic uses a 4 bit ACK/NAK. Any other value than 0xA is NAK
	MF_KEY_SIZE				= 6				# A Mifare Crypto1 key is 6 bytes

	# PICC types we can detect. Remember to update PICC_GetTypeName() if you add more
	# PICC_Type
	PICC_TYPE_UNKNOWN		= 0
	PICC_TYPE_ISO_14443_4	= 1				# PICC compliant with ISO/IEC 14443-4 
	PICC_TYPE_ISO_18092		= 2 			# PICC compliant with ISO/IEC 18092 (NFC)
	PICC_TYPE_MIFARE_MINI	= 3				# MIFARE Classic protocol, 320 bytes
	PICC_TYPE_MIFARE_1K		= 4				# MIFARE Classic protocol, 1KB
	PICC_TYPE_MIFARE_4K		= 5				# MIFARE Classic protocol, 4KB
	PICC_TYPE_MIFARE_UL		= 6				# MIFARE Ultralight or Ultralight C
	PICC_TYPE_MIFARE_PLUS	= 7				# MIFARE Plus
	PICC_TYPE_TNP3XXX		= 8				# Only mentioned in NXP AN 10833 MIFARE Type Identification Procedure
	PICC_TYPE_NOT_COMPLETE	= 255			# SAK indicates UID is not complete

	# Return codes from the functions in this class. Remember to update GetStatusCodeName() if you add more
	# StatusCode
	STATUS_OK				= 1				# Success
	STATUS_ERROR			= 2				# Error in communication
	STATUS_COLLISION		= 3				# Collission detected
	STATUS_TIMEOUT			= 4				# Timeout in communication
	STATUS_NO_ROOM			= 5				# A buffer is not big enough
	STATUS_INTERNAL_ERROR	= 6				# Internal error in the code. Should not happen ;-)
	STATUS_INVALID			= 7				# Invalid argument
	STATUS_CRC_WRONG		= 8				# The CRC_A does not match
	STATUS_MIFARE_NACK		= 9				# A MIFARE PICC responded with NAK

	# A struct used for passing the UID of a PICC
	class Uid:
		def __init__(self, size=None, uidByte=None, sak=None):
			self.size = size				# Number of bytes in the UID. 4, 7 or 10
			self.uidByte = [uidByte]*10
			self.sak = sak					# The SAK (Select acknowledge) byte returned from the PICC after successful selection

	# Member variables
	uid = Uid()								# Used by PICC_ReadCardSerial()

	# A struct used for passing a MIFARE Crypto1 key
	class MIFARE_Key:
		def __init__(self, keyByte=0xFF, ):
			self.keyByte = [keyByte]*MFRC522.MF_KEY_SIZE

	# Size of the MFRC522 FIFO
	FIFO_SIZE = 64							# The FIFO is 64 bytes

	Pin_rst = None

	logger = None
# ------------------------------------------------------------------------------
	def __init__(self, bus=0, device=0, spd=1000000, pin_mode=GPIO.BOARD, pin_rst=-1, logLevel='info'):
		README="""
			bus - задать шину;
			device - задать устройство;
			spd - задать скорость
			pin_mode - задать режим нумерации контактов:
				MODE_UNKNOWN -1
				BOARD		10
				BCM		  11
				SERIAL	   40
				SPI		  41
				I2C		  42
				PWM		  43
			pin_rst - задать номер gpio для управления reset-ом;
			logLevel - задать уровень логирования;
		"""
		self.spi = spidev.SpiDev()
		self.spi.open(bus, device)
		self.spi.max_speed_hz = spd

		self.logger = logging.getLogger('mfrc522Logger')

		LOGFILE = "./mfrc522.log"
		# Create handlers
		c_handler = logging.StreamHandler()
#		f_handler = logging.FileHandler(LOGFILE)

		c_format = logging.Formatter('[ %(levelname)s ] %(message)s')

		c_handler.setFormatter(c_format)
#		f_handler.setFormatter(f_format)

		# Add handlers to the logger
		if not logging.getLogger('mfrc522Logger').hasHandlers():
			self.logger.addHandler(c_handler)
#			self.logger.addHandler(f_handler)

		if type(logLevel) == type(str()):
			if   logLevel[:1].upper() == "D":	self.logLevel = logging.DEBUG
			elif logLevel[:1].upper() == "I":	self.logLevel = logging.INFO
			elif logLevel[:1].upper() == "W":	self.logLevel = logging.WARNING
			elif logLevel[:1].upper() == "E":	self.logLevel = logging.ERROR
			elif logLevel[:1].upper() == "C":	self.logLevel = logging.CRITICAL
			else:								self.logLevel = logging.INFO
		if logLevel in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]:
			self.logLevel = logLevel
		else:
			self.logLevel = logging.INFO

		self.logger.setLevel(self.logLevel)

		gpioMode = GPIO.getmode()
		self.logger.debug("gpioMode: {}".format(gpioMode))

		if pin_mode == -1:
			if gpioMode is None:
				GPIO.setmode(GPIO.BCM)
		else:
			GPIO.setmode(pin_mode)

		if pin_rst == -1:
			if pin_mode == GPIO.BCM:
				self.Pin_rst = 15
			else:
				self.Pin_rst = 22
		else:
			self.Pin_rst = pin_rst

		GPIO.setwarnings(False)
		GPIO.setup(self.Pin_rst, GPIO.OUT)
		GPIO.output(self.Pin_rst, 0)

		self.PCD_Init()

	def __del__(self):
		self.MFRC522_Close()

	def MFRC522_Close(self):
		self.logger.removeHandler(self.logger.handlers)
		self.spi.close()
		if GPIO is not None:
			GPIO.cleanup()

	# Writes a byte to the specified register in the MFRC522 chip
	# The interface is described in the datasheet section 8.1.2
	def PCD_WriteRegister(	self,			# The default name of the first argument for object methods
							addr,			# The register to write to. One of the PCD_Register enums
							val				# The value to write
						):
		# MSB == 0 is for writing. LSB is not used in address. Datasheet section 8.1.2.3
		self.spi.xfer2([addr & 0x7E, val])

	# Writes a number of bytes to the specified register in the MFRC522 chip
	# The interface is described in the datasheet section 8.1.2
	def PCD_WriteRegisterArray(	self,			# The default name of the first argument for object methods
								addr,			# The register to write to. One of the PCD_Register enums
								val,			# The value to write (должно быть списком)
								length=None		# The number of bytes to write to the register
								):
		# MSB == 0 is for writing. LSB is not used in address. Datasheet section 8.1.2.3
		length = length if length else len(val)

		self.spi.xfer2([addr & 0x7E] + val[:length])

	# Reads a byte from the specified register in the MFRC522 chip
	# The interface is described in the datasheet section 8.1.2
	def PCD_ReadRegister(self, addr):
		# MSB == 1 is for reading. LSB is not used in address. Datasheet section 8.1.2.3
		val = self.spi.xfer2([(addr & 0x7E) | 0x80, 0])
		return val[1]

	# Reads a number of bytes from the specified register in the MFRC522 chip
	# The interface is described in the datasheet section 8.1.2
	def PCD_ReadRegisterArray(	self,
								addr,		# The register to read from. One of the PCD_Register enums
								count,		# The number of bytes to read
								rxAlign=0	# Only bit positions rxAlign..7 in values[0] are updated
							):
		if not count:
			return

		values = [None]*count

		address = (addr & 0x7E) | 0x80		# MSB == 1 is for reading. LSB is not used in address. Datasheet section 8.1.2.3
		self.spi.xfer2([address])			# Tell MFRC522 which address we want to read
		for ix in range(count-1):
			if not ix and rxAlign:			# Only update bit positions rxAlign..7 in values[0]
				# Create bit mask for bit positions rxAlign..7
				mask = 0
				for iy in range(rxAlign, 8):
					mask |= (1 << iy)
				# Read value and tell that we want to read the same address again
				value = self.spi.xfer2([address])[0]
				# Apply mask to both current value of values[0] and the new data in value
				values[ix] = (values[ix] & (~mask)) | (value & mask)
			else:
				# Read value and tell that we want to read the same address again
				values[ix] = self.spi.xfer2([address])[0]

		# Read the final byte. Send 0 to stop reading
		values[count-1] = self.spi.xfer2([0])[0]

		return values

	# Sets the bits given in mask in register reg
	def PCD_SetRegisterBitMask(self, reg, mask):
		tmp = self.PCD_ReadRegister(reg)
		self.PCD_WriteRegister(reg, tmp | mask)

	# Clears the bits given in mask from register reg
	def PCD_ClearRegisterBitMask(self, reg, mask):
		tmp = self.PCD_ReadRegister(reg)
		self.PCD_WriteRegister(reg, tmp & (~mask))

	# Use the CRC coprocessor in the MFRC522 to calculate a CRC_A
	# @return STATUS_OK on success, STATUS_TIMEOUT otherwise
	# Out: Buffer. Result is written to result[0..1], low byte first
	def PCD_CalculateCRC(	self,
							data,									# In: The data to transfer to the FIFO for CRC calculation
							length=None								# In: The number of bytes to transfer
						):
		length = length if length else len(data)
		self.PCD_WriteRegister(self.CommandReg, self.PCD_Idle)		# Stop any active command
		self.PCD_WriteRegister(self.DivIrqReg, 0x04)				# Clear the CRCIRq interrupt request bit
		self.PCD_SetRegisterBitMask(self.FIFOLevelReg, 0x80)		# FlushBuffer = 1, FIFO initialization
		self.PCD_WriteRegisterArray(self.FIFODataReg, data, length)	# Write data to the FIFO
		self.PCD_WriteRegister(self.CommandReg, self.PCD_CalcCRC)	# Start the calculation

		# Wait for the CRC calculation to complete. Each iteration of the while-loop takes 17.73�s
		for ix in range(5000):
			# DivIrqReg[7..0] bits are: Set2 reserved reserved MfinActIRq reserved CRCIRq reserved reserved
			if self.PCD_ReadRegister(self.DivIrqReg) & 0x04:		# CRCIRq bit set - calculation done
				break
		else:														# The emergency break. We will eventually terminate on this one after 89ms. Communication with the MFRC522 might be down
			return [self.STATUS_TIMEOUT, None]

		self.PCD_WriteRegister(self.CommandReg, self.PCD_Idle)		# Stop calculating CRC for new content in the FIFO

		# Transfer the Result from the registers to the result buffer
		result = [	self.PCD_ReadRegister(self.CRCResultRegL),
					self.PCD_ReadRegister(self.CRCResultRegH)	]

		# Out: result buffer. Result is written to result[0..1], low byte first
		return [self.STATUS_OK, result]

#####################################################################################
#					Functions for manipulating the MFRC522							#
#####################################################################################

	# Initializes the MFRC522 chip
	def PCD_Init(self):
		self.logger.info("Start PCD_Init")
		if not GPIO.input(self.Pin_rst):
			GPIO.output(self.Pin_rst, 1)
			sleep(0.05)

		self.PCD_Reset()

		# When communicating with a PICC we need a timeout if something goes wrong
		# f_timer = 13.56 MHz / (2*TPreScaler+1) where TPreScaler = [TPrescaler_Hi:TPrescaler_Lo]
		# TPrescaler_Hi are the four low bits in TModeReg. TPrescaler_Lo is TPrescalerReg
#		self.PCD_WriteRegister(self.TModeReg, 0x80)			# TAuto=1; timer starts automatically at the end of the transmission in all communication modes at all speeds
#		self.PCD_WriteRegister(self.TPrescalerReg, 0xA9)	# TPreScaler = TModeReg[3..0]:TPrescalerReg, ie 0x0A9 = 169 => f_timer=40kHz, ie a timer period of 25us
		self.PCD_WriteRegister(self.TModeReg, 0x8D)
		self.PCD_WriteRegister(self.TPrescalerReg, 0x3E)

		self.PCD_WriteRegister(self.TReloadRegH, 0x03)		# Reload timer with 0x3E8 = 1000, ie 25ms before timeout
		self.PCD_WriteRegister(self.TReloadRegL, 0xE8)
		
		self.PCD_WriteRegister(self.TxASKReg, 0x40)			# Default 0x00. Force a 100 % ASK modulation independent of the ModGsPReg register setting
		self.PCD_WriteRegister(self.ModeReg, 0x3D)			# Default 0x3F. Set the preset value for the CRC coprocessor for the CalcCRC command to 0x6363 (ISO 14443-3 part 6.2.4)
		self.PCD_AntennaOn()								# Enable the antenna driver pins TX1 and TX2 (they were disabled by the reset)

	# Performs a soft reset on the MFRC522 chip and waits for it to be ready again
	def PCD_Reset(self):
		self.PCD_WriteRegister(self.CommandReg, self.PCD_SoftReset)	# Issue the SoftReset command
		# The datasheet does not mention how long the SoftRest command takes to complete
		# But the MFRC522 might have been in soft power-down mode (triggered by bit 4 of CommandReg)
		# Section 8.8.2 in the datasheet says the oscillator start-up time is the start up time of the crystal + 37,74�s. Let us be generous: 50ms
		sleep(0.05)
		# Wait for the PowerDown bit in CommandReg to be cleared
		while (self.PCD_ReadRegister(self.CommandReg) & (1<<4)):
			# PCD still restarting - unlikely after waiting 50ms, but better safe than sorry
			pass

	# Turns the antenna on by enabling pins TX1 and TX2
	# After a reset these pins are disabled
	def PCD_AntennaOn(self):
		value = self.PCD_ReadRegister(self.TxControlReg)
		if (value & 0x03) != 0x03:
			self.PCD_WriteRegister(self.TxControlReg, value | 0x03)

	# Turns the antenna off by disabling pins TX1 and TX2
	def PCD_AntennaOff(self):
		self.PCD_ClearRegisterBitMask(self.TxControlReg, 0x03)

	# Get the current MFRC522 Receiver Gain (RxGain[2:0]) value
	# See 9.3.3.6 / table 98 in http:#www.nxp.com/documents/data_sheet/MFRC522.pdf
	# NOTE: Return value scrubbed with (0x07<<4)=01110000b as RCFfgReg may use reserved bits
	# 
	# @return Value of the RxGain, scrubbed to the 3 bits used
	def PCD_GetAntennaGain(self):
		return self.PCD_ReadRegister(self.RFCfgReg) & (0x07<<4)

	# Set the MFRC522 Receiver Gain (RxGain) to value specified by given mask
	# See 9.3.3.6 / table 98 in http:#www.nxp.com/documents/data_sheet/MFRC522.pdf
	# NOTE: Given mask is scrubbed with (0x07<<4)=01110000b as RCFfgReg may use reserved bits
	def PCD_SetAntennaGain(self, mask):
		if self.PCD_GetAntennaGain() != mask:						# only bother if there is a change
			self.PCD_ClearRegisterBitMask(self.RFCfgReg, (0x07<<4))		# clear needed to allow 000 pattern
			self.PCD_SetRegisterBitMask(self.RFCfgReg, mask & (0x07<<4))	# only set RxGain[2:0] bits

	# Performs a self-test of the MFRC522
	# See 16.1.1 in http:#www.nxp.com/documents/data_sheet/MFRC522.pdf
	# 
	# @return Whether or not the test passed
	def PCD_PerformSelfTest(self):
		# This follows directly the steps outlined in 16.1.1
		# 1. Perform a soft reset
		self.PCD_Reset()

		# 2. Clear the internal buffer by writing 25 bytes of 00h
		ZEROES = [0x00]*25
		self.PCD_SetRegisterBitMask(self.FIFOLevelReg, 0x80) # flush the FIFO buffer
		self.PCD_WriteRegisterArray(self.FIFODataReg, ZEROES) # write 25 bytes of 00h to FIFO
		self.PCD_WriteRegister(self.CommandReg, self.PCD_Mem) # transfer to internal buffer

		# 3. Enable self-test
		self.PCD_WriteRegister(self.AutoTestReg, 0x09)

		# 4. Write 00h to FIFO buffer
		self.PCD_WriteRegister(self.FIFODataReg, 0x00)

		# 5. Start self-test by issuing the CalcCRC command
		self.PCD_WriteRegister(self.CommandReg, self.PCD_CalcCRC)

		# 6. Wait for self-test to complete
		for ix in range(0xFF):
			# DivIrqReg[7..0] bits are: Set2 reserved reserved MfinActIRq reserved CRCIRq reserved reserved
			if (self.PCD_ReadRegister(self.DivIrqReg) & 0x04):		# CRCIRq bit set - calculation done
				break
		self.PCD_WriteRegister(self.CommandReg, self.PCD_Idle)		# Stop calculating CRC for new content in the FIFO

		# 7. Read out resulting 64 bytes from the FIFO buffer
		result = self.PCD_ReadRegisterArray(self.FIFODataReg, 64, 0)

		# Auto self-test done
		# Reset AutoTestReg register to be 0 again. Required for normal operation
		self.PCD_WriteRegister(self.AutoTestReg, 0x00)

		# Determine firmware version (see section 9.3.4.8 in spec)
		version = self.PCD_ReadRegister(self.VersionReg)

		# Pick the appropriate reference values
		if version == 0x91:			# Version 1.0
			reference = self.MFRC522_firmware_referenceV1_0
		elif version == 0x92:		# Version 2.0
			reference = self.MFRC522_firmware_referenceV2_0
		else:
			return false 			# Unknown version

		# Verify that the results match up to our expectations
		for ix in range(64):
			if result[ix] != reference[ix]:
				return false

		# Test passed; all is good
		return true

################################################################################
#				Functions for communicating with PICCs						   #
################################################################################

	# Executes the Transceive command
	# CRC validation can only be done if backData and backLen are specified
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def PCD_TransceiveData(	self,
							sendData,		# The data to transfer to the FIFO
							sendLen=None,	# Number of bytes to transfer to the FIFO
							backLen=None,	# NULL or buffer if data should be read back after executing the command
							validBits=None,	# In/Out: The number of valid bits in the last byte. 0 for 8 valid bits. Default NULL
							rxAlign=0,		# In: Defines the bit position in backData[0] for the first bit received. Default 0
							checkCRC=False	# In: True => The last two bytes of the response is assumed to be a CRC_A that must be validated
							):
		waitIRq = 0x30						# RxIRq and IdleIRq
		sendLen = sendLen if sendLen else len(sendData)

		return self.PCD_CommunicateWithPICC(self.PCD_Transceive, waitIRq, sendData, sendLen, backLen, validBits, rxAlign, checkCRC)

	# Transfers data to the MFRC522 FIFO, executes a command, waits for completion and transfers data back from the FIFO
	# CRC validation can only be done if backLen are specified
	#
	# @return STATUS_OK on success, STATUS_??? otherwise
	#/
	def PCD_CommunicateWithPICC(self,
								command,		# The command to execute. One of the PCD_Command enums
								waitIRq,		# The bits in the ComIrqReg register that signals successful completion of the command
								sendData,		# The data to transfer to the FIFO
								sendLen=None,	# Number of bytes to transfer to the FIFO
								backLen=None,	# Number byte if data should be read back after executing the command
								validBits=None,	# In/Out: The number of valid bits in the last byte. 0 for 8 valid bits
								rxAlign=0,		# In: Defines the bit position in backData[0] for the first bit received. Default 0
								checkCRC=False	# In: True => The last two bytes of the response is assumed to be a CRC_A that must be validated
								):
		# Prepare values for BitFramingReg
		txLastBits = validBits if validBits else 0
		bitFraming = (rxAlign << 4) + txLastBits						# RxAlign = BitFramingReg[6..4]. TxLastBits = BitFramingReg[2..0]

		sendLen = sendLen if sendLen else len(sendData)

		self.PCD_WriteRegister(self.CommandReg, self.PCD_Idle)			# Stop any active command
		self.PCD_WriteRegister(self.ComIrqReg, 0x7F)					# Clear all seven interrupt request bits
		self.PCD_SetRegisterBitMask(self.FIFOLevelReg, 0x80)			# FlushBuffer = 1, FIFO initialization
		self.PCD_WriteRegisterArray(self.FIFODataReg, sendData, sendLen)# Write sendData to the FIFO
		self.PCD_WriteRegister(self.BitFramingReg, bitFraming)			# Bit adjustments
		self.PCD_WriteRegister(self.CommandReg, command)				# Execute the command
		if command == self.PCD_Transceive:
			self.PCD_SetRegisterBitMask(self.BitFramingReg, 0x80)		# StartSend=1, transmission of data starts

		# Wait for the command to complete
		# In PCD_Init() we set the TAuto flag in TModeReg. This means the timer automatically starts when the PCD stops transmitting
		# Each iteration of the loop takes 17.86us (на Cpp а в python??)
		for ix in range(2000):
			n = self.PCD_ReadRegister(self.ComIrqReg)					# ComIrqReg[7..0] bits are: Set1 TxIRq RxIRq IdleIRq HiAlertIRq LoAlertIRq ErrIRq TimerIRq
			if n & waitIRq:												# One of the interrupts that signal success has been set
				break
			if n & 0x01:												# Timer interrupt - nothing received in 25ms
				self.logger.debug("n: {}".format(n))
				return [self.STATUS_TIMEOUT, None, None, validBits]
		else:
			# The emergency break. If all other condions fail we will eventually terminate on this one after 35.7ms. Communication with the MFRC522 might be down
			return [self.STATUS_TIMEOUT, None, None, validBits]

		# Stop now if any errors except collisions were detected
		errorRegValue = self.PCD_ReadRegister(self.ErrorReg)			# ErrorReg[7..0] bits are: WrErr TempErr reserved BufferOvfl CollErr CRCErr ParityErr ProtocolErr
		self.logger.debug("errorRegValue: {}".format(errorRegValue))
		if errorRegValue & 0x13:										# BufferOvfl ParityErr ProtocolErr
			return [self.STATUS_ERROR, None, None, validBits]

		self.logger.debug("backLen: {}".format(backLen))

		# If the caller wants data back, get it from the MFRC522
		if backLen:
			backLen = self.PCD_ReadRegister(self.FIFOLevelReg)			# Number of bytes in the FIFO
			backData = self.PCD_ReadRegisterArray(self.FIFODataReg, backLen, rxAlign)		# Get received data from FIFO
			_validBits = self.PCD_ReadRegister(self.ControlReg) & 0x07	# RxLastBits[2:0] indicates the number of valid bits in the last received byte. If this value is 000b, the whole byte is valid
			if validBits:
				validBits = _validBits

			self.logger.debug("backLen: {}, backData: {}".format(backLen, backData))
		else:
			backData = None

		# Tell about collisions
		if errorRegValue & 0x08:										# CollErr
			return [self.STATUS_COLLISION, None, None, validBits]

		# Perform CRC_A validation if requested
		if backData and backLen and checkCRC:
			# In this case a MIFARE Classic NAK is not OK
			if backLen == 1 and _validBits == 4:
				return [self.STATUS_MIFARE_NACK, None, None, validBits]
			# We need at least the CRC_A value and all 8 bits of the last byte must be received
			if backLen < 2 or _validBits != 0:
				return [self.STATUS_CRC_WRONG, None, None, validBits]
			# Verify CRC_A - do our own calculation and store the control in controlBuffer
			status, controlBuffer = self.PCD_CalculateCRC(backData, backLen-2)
			if status != self.STATUS_OK:
				return [status, None, None, validBits]
			if (backData[backLen-2] != controlBuffer[0]) or (backData[backLen-1] != controlBuffer[1]):
				return [self.STATUS_CRC_WRONG, None, None, validBits]

		self.logger.debug("status: {}, backData: {}, backLen: {}, validBits: {}".format(self.STATUS_OK, backData, backLen, validBits))
		return [self.STATUS_OK, backData, backLen, validBits]

	# Transmits a REQuest command, Type A. Invites PICCs in state IDLE to go to READY and prepare for anticollision or selection. 7 bit frame
	# Beware: When two PICCs are in the field at the same time I often get STATUS_TIMEOUT - probably due do bad antenna design
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def PICC_RequestA(	self,
						bufferSize			# Buffer size, at least two bytes. Also number of bytes returned if STATUS_OK
						):
		# bufferATQA - The buffer to store the ATQA (Answer to request) in
		return self.PICC_REQA_or_WUPA([self.PICC_CMD_REQA], bufferSize)

	# Transmits a Wake-UP command, Type A. Invites PICCs in state IDLE and HALT to go to READY(*) and prepare for anticollision or selection. 7 bit frame
	# Beware: When two PICCs are in the field at the same time I often get STATUS_TIMEOUT - probably due do bad antenna design
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def PICC_WakeupA(	self,
						bufferSize			# Buffer size, at least two bytes. Also number of bytes returned if STATUS_OK
					):
		# bufferATQA - The buffer to store the ATQA (Answer to request) in
		return self.PICC_REQA_or_WUPA([self.PICC_CMD_WUPA], bufferSize)

	# Transmits REQA or WUPA commands
	# Beware: When two PICCs are in the field at the same time I often get STATUS_TIMEOUT - probably due do bad antenna design
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def PICC_REQA_or_WUPA(	self,
							command, 						# The command to send - PICC_CMD_REQA or PICC_CMD_WUPA
							bufferSize						# Buffer size, at least two bytes. Also number of bytes returned if STATUS_OK
						):
		if bufferSize < 2:									# The ATQA response is 2 bytes long
			return [self.STATUS_NO_ROOM, None]

		self.PCD_ClearRegisterBitMask(self.CollReg, 0x80)	# ValuesAfterColl=1 => Bits received after collision are cleared
		validBits = 7;										# For REQA and WUPA we need the short frame format - transmit only 7 bits of the last (and only) byte. TxLastBits = BitFramingReg[2..0]
		# bufferATQA - The buffer to store the ATQA (Answer to request) in
		status, bufferATQA, bufferSize, validBits = self.PCD_TransceiveData(command, 1, bufferSize, validBits)
		if status != self.STATUS_OK:
			return [status, None]

		if bufferSize != 2 or validBits != 0:				# ATQA must be exactly 16 bits
			return [self.STATUS_ERROR, None]

		return [self.STATUS_OK, bufferATQA]

	# Transmits SELECT/ANTICOLLISION commands to select a single PICC
	# Before calling this function the PICCs must be placed in the READY(*) state by calling PICC_RequestA() or PICC_WakeupA()
	# On success:
	# 		- The chosen PICC is in state ACTIVE(*) and all other PICCs have returned to state IDLE/HALT. (Figure 7 of the ISO/IEC 14443-3 draft.)
	# 		- The UID size and value of the chosen PICC is returned in *uid along with the SAK
	# 
	# A PICC UID consists of 4, 7 or 10 bytes
	# Only 4 bytes can be specified in a SELECT command, so for the longer UIDs two or three iterations are used:
	# 		UID size	Number of UID bytes		Cascade levels		Example of PICC
	# 		========	===================		==============		===============
	# 		single				 4						1				MIFARE Classic
	# 		double				 7						2				MIFARE Ultralight
	# 		triple				10						3				Not currently in use?
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def PICC_Select(	self,
						validBits=0		# The number of known UID bits supplied in *uid. Normally 0. If set you must also supply uid.size
					):
		"""
		# Uid struct - определена глобально. Normally output, but can also be used to supply a known UID

		bool uidComplete
		bool selectDone
		bool useCascadeTag
		byte cascadeLevel = 1
		byte result
		byte count
		byte index
		byte uidIndex;					# The first index in uid.uidByte[] that is used in the current Cascade Level
		char currentLevelKnownBits;		# The number of known UID bits in the current Cascade Level
		byte buffer[9];					# The SELECT/ANTICOLLISION commands uses a 7 byte standard frame + 2 bytes CRC_A
		byte bufferUsed;				# The number of bytes used in the buffer, ie the number of bytes to transfer to the FIFO
		byte rxAlign;					# Used in BitFramingReg. Defines the bit position for the first bit received
		byte txLastBits;				# Used in BitFramingReg. The number of valid bits in the last transmitted byte. 
		byte *responseBuffer
		byte responseLength"""

		cascadeLevel = 1
		buffer = [None]*9

		# Description of buffer structure:
		#		Byte 0: SEL 				Indicates the Cascade Level: PICC_CMD_SEL_CL1, PICC_CMD_SEL_CL2 or PICC_CMD_SEL_CL3
		#		Byte 1: NVB					Number of Valid Bits (in complete command, not just the UID): High nibble: complete bytes, Low nibble: Extra bits. 
		#		Byte 2: UID-data or CT		See explanation below. CT means Cascade Tag
		#		Byte 3: UID-data
		#		Byte 4: UID-data
		#		Byte 5: UID-data
		#		Byte 6: BCC					Block Check Character - XOR of bytes 2-5
		#		Byte 7: CRC_A
		#		Byte 8: CRC_A
		# The BCC and CRC_A is only transmitted if we know all the UID bits of the current Cascade Level
		#
		# Description of bytes 2-5: (Section 6.5.4 of the ISO/IEC 14443-3 draft: UID contents and cascade levels)
		#		UID size	Cascade level	Byte2	Byte3	Byte4	Byte5
		#		========	=============	=====	=====	=====	=====
		#		 4 bytes		1			uid0	uid1	uid2	uid3
		#		 7 bytes		1			CT		uid0	uid1	uid2
		#						2			uid3	uid4	uid5	uid6
		#		10 bytes		1			CT		uid0	uid1	uid2
		#						2			CT		uid3	uid4	uid5
		#						3			uid6	uid7	uid8	uid9

		# Sanity checks
		if validBits > 80:
			return self.STATUS_INVALID

		# Prepare MFRC522
		self.PCD_ClearRegisterBitMask(self.CollReg, 0x80)		# ValuesAfterColl=1 => Bits received after collision are cleared

		# Repeat Cascade Level loop until we have a complete UID
		uidComplete = False
		while not uidComplete:
			# Set the Cascade Level in the SEL byte, find out if we need to use the Cascade Tag in byte 2
			if cascadeLevel == 1:
				buffer[0] = self.PICC_CMD_SEL_CL1
				uidIndex = 0
				useCascadeTag = validBits and self.uid.size > 4	# When we know that the UID has more than 4 bytes
			elif cascadeLevel == 2:
				buffer[0] = self.PICC_CMD_SEL_CL2
				uidIndex = 3
				useCascadeTag = validBits and self.uid.size > 7	# When we know that the UID has more than 7 bytes
			elif cascadeLevel == 3:
				buffer[0] = self.PICC_CMD_SEL_CL3
				uidIndex = 6
				useCascadeTag = False						# Never used in CL3
			else:
				return self.STATUS_INTERNAL_ERROR

			self.logger.debug("buffer[0]: {}, uidIndex: {}, useCascadeTag: {}".format(buffer[0], uidIndex, useCascadeTag))

			# How many UID bits are known in this Cascade Level?
			currentLevelKnownBits = validBits - (8 * uidIndex)
			if currentLevelKnownBits < 0:
				currentLevelKnownBits = 0

			# Copy the known bits from uid.uidByte[] to buffer[]
			index = 2 # destination index in buffer[]
			if useCascadeTag:
				buffer[index] = self.PICC_CMD_CT
				index += 1

			bytesToCopy = int(currentLevelKnownBits / 8) + (1 if currentLevelKnownBits % 8 else 0) # The number of bytes needed to represent the known bits for this level
			if bytesToCopy:
				maxBytes = 3 if useCascadeTag else 4	# Max 4 bytes in each Cascade Level. Only 3 left if we use the Cascade Tag
				if bytesToCopy > maxBytes:
					bytesToCopy = maxBytes

				for count in range(bytesToCopy):
					buffer[index] = self.uid.uidByte[uidIndex + count]
					index += 1

			# Now that the data has been copied we need to include the 8 bits in CT in currentLevelKnownBits
			if useCascadeTag:
				currentLevelKnownBits += 8
			
			# Repeat anti collision loop until we can transmit all UID bits + BCC and receive a SAK - max 32 iterations

			selectDone = False
			while not selectDone:
				# Find out how many bits and bytes to send and receive
				if currentLevelKnownBits >= 32:			# All UID bits in this Cascade Level are known. This is a SELECT
					#print(("SELECT: currentLevelKnownBits=")); print(currentLevelKnownBits, DEC)
					buffer[1] = 0x70					# NVB - Number of Valid Bits: Seven whole bytes
					# Calculate BCC - Block Check Character
					buffer[6] = buffer[2] ^ buffer[3] ^ buffer[4] ^ buffer[5]

					# Calculate CRC_A
					l = 7
					status, result = self.PCD_CalculateCRC(buffer, l)

					# полученную CRC первых 7-ми (l) байт кладём 7-ым и 8-мым байтами
					buffer = buffer[:l] + result
#					for ix in range(l,l+2): buffer[ix] = result[ix-l]
					if status != self.STATUS_OK:
						return status

					txLastBits		= 0		# 0 => All 8 bits are valid
					bufferUsed		= 9
					# Store response in the last 3 bytes of buffer (BCC and CRC_A - not needed after tx)
					bufferOffset	= 6
					responseLength	= 3
				else:	# This is an ANTICOLLISION
					#print(("ANTICOLLISION: currentLevelKnownBits=")); print(currentLevelKnownBits, DEC)
					txLastBits		= currentLevelKnownBits % 8
					count			= int(currentLevelKnownBits / 8)		# Number of whole bytes in the UID part
					index			= 2 + count						# Number of whole bytes: SEL + NVB + UIDs
					buffer[1]		= (index << 4) + txLastBits		# NVB - Number of Valid Bits
					bufferUsed		= index + (1 if txLastBits else 0)
					# Store response in the unused part of buffer
					bufferOffset	= index
					responseLength	= len(buffer) - index
				
				# Set bit adjustments
				rxAlign = txLastBits								# Having a seperate variable is overkill. But it makes the next line easier to read
				# RxAlign = BitFramingReg[6..4]. TxLastBits = BitFramingReg[2..0]
				self.PCD_WriteRegister(self.BitFramingReg, (rxAlign << 4) + txLastBits)

				# Transmit the buffer and receive the response
				self.logger.debug("buffer: {}, bufferUsed: {}, bufferOffset: {}, responseLength: {}, txLastBits: {}".format(buffer, bufferUsed, bufferOffset, responseLength, txLastBits))
				status, responseBuffer, responseLength, txLastBits = self.PCD_TransceiveData(buffer, bufferUsed, responseLength, txLastBits, rxAlign)
				self.logger.debug("status: {}, responseBuffer: {}, responseLength: {}, txLastBits: {}".format(status, responseBuffer, responseLength, txLastBits))

				if status == self.STATUS_COLLISION:					# More than one PICC in the field => collision
					status = self.PCD_ReadRegister(self.CollReg)	# CollReg[7..0] bits are: ValuesAfterColl reserved CollPosNotValid CollPos[4:0]
					if status & 0x20:								# CollPosNotValid
						return self.STATUS_COLLISION				# Without a valid collision position we cannot continue

					collisionPos = status & 0x1F					# Values 0-31, 0 means bit 32
					if collisionPos == 0:
						collisionPos = 32

					if collisionPos <= currentLevelKnownBits:		# No progress - should not happen
						return self.STATUS_INTERNAL_ERROR

					# Choose the PICC with the bit set
					currentLevelKnownBits = collisionPos
					count			= (currentLevelKnownBits - 1) % 8	# The bit to modify
					index			= 1 + int(currentLevelKnownBits / 8) + (1 if count else 0)		# First byte is index 0
					buffer[index]	|= (1 << count)

				elif status != self.STATUS_OK:
					return status
				else:												# STATUS_OK
					if currentLevelKnownBits >= 32:					# This was a SELECT
						selectDone = True							# No more anticollision 
						# We continue below outside the while
					else:											# This was an ANTICOLLISION
						# We now have all 32 bits of the UID in this Cascade Level
						currentLevelKnownBits = 32
						# Run loop again to do the SELECT
					for ix in range(bufferOffset,bufferOffset+responseLength):
						buffer[ix] = responseBuffer[ix-bufferOffset]
			
			# We do not check the CBB - it was constructed by us above
			
			# Copy the found UID bytes from buffer[] to uid.uidByte[]
			index			= 3 if buffer[2] == self.PICC_CMD_CT else 2	# source index in buffer[]
			bytesToCopy		= 3 if buffer[2] == self.PICC_CMD_CT else 4
			self.logger.debug("buffer[2]: {}, self.PICC_CMD_CT: {}, index: {}, bytesToCopy: {}".format(buffer[2], self.PICC_CMD_CT, index, bytesToCopy))
			for count in range(bytesToCopy):
				self.uid.uidByte[uidIndex + count] = buffer[index]
				index += 1

			# Check response SAK (Select Acknowledge)
			if responseLength != 3 or txLastBits != 0:				# SAK must be exactly 24 bits (1 byte + CRC_A)
				return self.STATUS_ERROR

			# Verify CRC_A - do our own calculation and store the control in buffer[2..3] - those bytes are not needed anymore
			status, result = self.PCD_CalculateCRC(responseBuffer, 1)
			l = 2
			for ix in range(l,l+2): buffer[ix] = result[ix-l]

			if status != self.STATUS_OK:
				return status

			if buffer[2] != responseBuffer[1] or buffer[3] != responseBuffer[2]:
				return self.STATUS_CRC_WRONG

			if responseBuffer[0] & 0x04:							# Cascade bit set - UID not complete yes
				cascadeLevel += 1

			else:
				uidComplete = True
				self.uid.sak = responseBuffer[0]

		# Set correct uid.size
		self.uid.size = 3 * cascadeLevel + 1

		result = ""
		for ix in range(self.uid.size):
			if self.uid.uidByte[ix] != None:
				result += "0x{:02X} ".format(self.uid.uidByte[ix])
			else:
				self.logger.error("not correct uid")
				break
		self.logger.info("UID: {}".format(result))

		return self.STATUS_OK

	# Instructs a PICC in state ACTIVE(*) to go to state HALT
	#
	# @return STATUS_OK on success, STATUS_??? otherwise
	def PICC_HaltA(self):

		# Build command buffer
		buffer = [self.PICC_CMD_HLTA, 0]
		# Calculate CRC_A
		status, result = self.PCD_CalculateCRC(buffer)
		buffer += result
		self.logger.debug("status: {}, buffer: {}".format(status, buffer))
		if status != self.STATUS_OK:
			return status

		# Send the command
		# The standard says:
		#		If the PICC responds with any modulation during a period of 1 ms after the end of the frame containing the
		#		HLTA command, this response shall be interpreted as 'not acknowledge'
		# We interpret that this way: Only STATUS_TIMEOUT is an success
		status, result = self.PCD_TransceiveData(buffer)[:2]
		self.logger.debug("status: {}, result: {}".format(status, result))
		if status == self.STATUS_TIMEOUT:
			return self.STATUS_OK

		if status == self.STATUS_OK: # That is ironically NOT ok in this case ;-)
			return self.STATUS_ERROR

		return status

################################################################################
#			 	Functions for communicating with MIFARE PICCs				   #
################################################################################

	# Executes the MFRC522 MFAuthent command
	# This command manages MIFARE authentication to enable a secure communication to any MIFARE Mini, MIFARE 1K and MIFARE 4K card
	# The authentication is described in the MFRC522 datasheet section 10.3.1.9 and http:#www.nxp.com/documents/data_sheet/MF1S503x.pdf section 10.1
	# For use with MIFARE Classic PICCs
	# The PICC must be selected - ie in state ACTIVE(*) - before calling this function
	# Remember to call PCD_StopCrypto1() after communicating with the authenticated PICC - otherwise no new communications can start
	# 
	# All keys are set to FFFFFFFFFFFFh at chip delivery
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise. Probably STATUS_TIMEOUT if you supply the wrong key
	def PCD_Authenticate(	self,
							command,		# PICC_CMD_MF_AUTH_KEY_A or PICC_CMD_MF_AUTH_KEY_B
							blockAddr,		# The block number. See numbering in the comments in the .h file
							key,			# The MIFARE_key Crypteo1 key to use (6 bytes)
							uid				# Uid class. The first 4 bytes of the UID is used
						):
		waitIRq = 0x10						# IdleIRq

		# Build command buffer
		sendData = [None]*(6+self.MF_KEY_SIZE)
		sendData[0] = command
		sendData[1] = blockAddr
		for ix in range(self.MF_KEY_SIZE):		# 6 key bytes
			sendData[2+ix] = key.keyByte[ix]

		for ix in range(4):					# The first 4 bytes of the UID
			sendData[2+self.MF_KEY_SIZE+ix] = uid.uidByte[ix]

		self.logger.debug("command: {}, blockAddr: {}, key.keyByte: {}, uid.uidByte: {}, self.MF_KEY_SIZE: {}".format(command, blockAddr, key.keyByte, uid.uidByte, self.MF_KEY_SIZE))
		# Start the authentication
		return self.PCD_CommunicateWithPICC(self.PCD_MFAuthent, waitIRq, sendData)[:1]

	# Used to exit the PCD from its authenticated state
	# Remember to call this function after communicating with an authenticated PICC - otherwise no new communications can start
	def PCD_StopCrypto1(self):
		# Clear MFCrypto1On bit
		self.PCD_ClearRegisterBitMask(self.Status2Reg, 0x08) # Status2Reg[7..0] bits are: TempSensClear I2CForceHS reserved reserved MFCrypto1On ModemState[2:0]

	# Reads 16 bytes (+ 2 bytes CRC_A) from the active PICC
	# 
	# For MIFARE Classic the sector containing the block must be authenticated before calling this function
	# 
	# For MIFARE Ultralight only addresses 00h to 0Fh are decoded
	# The MF0ICU1 returns a NAK for higher addresses
	# The MF0ICU1 responds to the READ command by sending 16 bytes starting from the page address defined by the command argument
	# For example; if blockAddr is 03h then pages 03h, 04h, 05h, 06h are returned
	# A roll-back is implemented: If blockAddr is 0Eh, then the contents of pages 0Eh, 0Fh, 00h and 01h are returned
	# 
	# The buffer must be at least 18 bytes because a CRC_A is also returned
	# Checks the CRC_A before returning STATUS_OK
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_Read(	self,
						blockAddr,			# MIFARE Classic: The block (0-0xff) number. MIFARE Ultralight: The first page to return data from
						bufferSize			# Buffer size, at least 18 bytes. Also number of bytes returned if STATUS_OK
					):
		# Sanity check
		if bufferSize < 18:
			return self.STATUS_NO_ROOM

		# Build command buffer
		buffer = [None]*bufferSize
		buffer[0] = self.PICC_CMD_MF_READ
		buffer[1] = blockAddr
		# Calculate CRC_A
		l = 2
		status, result = self.PCD_CalculateCRC(buffer, 2)
		for ix in range(l,l+2): buffer[ix] = result[ix-l]
		
		if status != self.STATUS_OK:
			return [status, None]

		# Transmit the buffer and receive the response, validate CRC_A
		return self.PCD_TransceiveData(buffer, 4, bufferSize, None, 0, True)[:2]

	# Writes 16 bytes to the active PICC
	# 
	# For MIFARE Classic the sector containing the block must be authenticated before calling this function
	# 
	# For MIFARE Ultralight the operation is called "COMPATIBILITY WRITE"
	# Even though 16 bytes are transferred to the Ultralight PICC, only the least significant 4 bytes (bytes 0 to 3)
	# are written to the specified address. It is recommended to set the remaining bytes 04h to 0Fh to all logic 0
	# * 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_Write(	self,
						blockAddr,			# MIFARE Classic: The block (0-0xff) number. MIFARE Ultralight: The page (2-15) to write to
						buffer,				# The 16 bytes to write to the PICC
						bufferSize=None		# Buffer size, must be at least 16 bytes. Exactly 16 bytes are written
					):
		# Sanity check
		bufferSize = bufferSize if bufferSize else len(buffer)
		self.logger.debug("blockAddr: {}, buffer: {}, bufferSize: {}".format(blockAddr, buffer, bufferSize))
		if buffer == None or bufferSize < 16:
			return self.STATUS_INVALID

		# Mifare Classic protocol requires two communications to perform a write
		# Step 1: Tell the PICC we want to write to block blockAddr
		status = self.PCD_MIFARE_Transceive([self.PICC_CMD_MF_WRITE, blockAddr])		# Adds CRC_A and checks that the response is MF_ACK
		self.logger.debug("status: {}".format(status))
		if status != self.STATUS_OK:
			return status

		# Step 2: Transfer the data
		self.logger.debug("buffer: {}, bufferSize: {}".format(buffer, bufferSize))
		return self.PCD_MIFARE_Transceive(buffer, bufferSize)

	# Writes a 4 byte page to the active MIFARE Ultralight PICC
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_Ultralight_Write(	self,
									page,		# The page (2-15) to write to
									buffer		# The 4 bytes to write to the PICC. Buffer size, must be at least 4 bytes. Exactly 4 bytes are written
								):
		# Sanity check
		if buffer == None or len(buffer) < 4:
			return self.STATUS_INVALID

		# Build commmand buffer
		cmdBuffer = [self.PICC_CMD_UL_WRITE, page] + buffer[:4]

		# Perform the write
		return self.PCD_MIFARE_Transceive(cmdBuffer); # Adds CRC_A and checks that the response is MF_ACK

	# MIFARE Decrement subtracts the delta from the value of the addressed block, and stores the result in a volatile memory
	# For MIFARE Classic only. The sector containing the block must be authenticated before calling this function
	# Only for blocks in "value block" mode, ie with access bits [C1 C2 C3] = [110] or [001]
	# Use MIFARE_Transfer() to store the result in a block
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_Decrement(	self,
							blockAddr,			# The block (0-0xff) number
							delta=[None]*4		# This number is subtracted from the value of block blockAddr
						):
		return self.MIFARE_TwoStepHelper(self.PICC_CMD_MF_DECREMENT, blockAddr, delta)

	# MIFARE Increment adds the delta to the value of the addressed block, and stores the result in a volatile memory
	# For MIFARE Classic only. The sector containing the block must be authenticated before calling this function
	# Only for blocks in "value block" mode, ie with access bits [C1 C2 C3] = [110] or [001]
	# Use MIFARE_Transfer() to store the result in a block
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_Increment(	self,
							blockAddr,			# The block (0-0xff) number
							delta=[None]*4		# This number is added to the value of block blockAddr
						):
		return self.MIFARE_TwoStepHelper(self.PICC_CMD_MF_INCREMENT, blockAddr, delta)

	# MIFARE Restore copies the value of the addressed block into a volatile memory
	# For MIFARE Classic only. The sector containing the block must be authenticated before calling this function
	# Only for blocks in "value block" mode, ie with access bits [C1 C2 C3] = [110] or [001]
	# Use MIFARE_Transfer() to store the result in a block
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_Restore(	self,
						blockAddr				# The block (0-0xff) number
						):
		# The datasheet describes Restore as a two step operation, but does not explain what data to transfer in step 2
		# Doing only a single step does not work, so I chose to transfer 0L in step two
		return self.MIFARE_TwoStepHelper(self.PICC_CMD_MF_RESTORE, blockAddr, [0,0,0,0])

	# Helper function for the two-step MIFARE Classic protocol operations Decrement, Increment and Restore
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_TwoStepHelper(	self,
								command,		# The command to use
								blockAddr,		# The block (0-0xff) number
								data			# The data to transfer in step 2
							):
		# Step 1: Tell the PICC the command and block address
		status = self.PCD_MIFARE_Transceive([command, blockAddr])		# Adds CRC_A and checks that the response is MF_ACK
		if status != self.STATUS_OK:
			return status

		# Step 2: Transfer the data
		return self.PCD_MIFARE_Transceive(data, 4, True)				# Adds CRC_A and accept timeout as success

	# MIFARE Transfer writes the value stored in the volatile memory into one MIFARE Classic block
	# For MIFARE Classic only. The sector containing the block must be authenticated before calling this function
	# Only for blocks in "value block" mode, ie with access bits [C1 C2 C3] = [110] or [001]
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_Transfer(	self,
							blockAddr			# The block (0-0xff) number
						):
		# Tell the PICC we want to transfer the result into block blockAddr
		return self.PCD_MIFARE_Transceive([self.PICC_CMD_MF_TRANSFER, blockAddr])		# Adds CRC_A and checks that the response is MF_ACK

	# Helper routine to read the current value from a Value Block
	# 
	# Only for MIFARE Classic and only for blocks in "value block" mode, that
	# is: with access bits [C1 C2 C3] = [110] or [001]. The sector containing
	# the block must be authenticated before calling this function. 
	# 
	# @param[in]   blockAddr   The block (0x00-0xff) number
	# @param[out]  value	   Current value of the Value Block
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_GetValue(	self,
							blockAddr
						):
		# Read the block
		status, buffer = self.MIFARE_Read(blockAddr, 18)
		if status == self.STATUS_OK:
			# Extract the value
			return [status, int(buffer[3]<<24) + int(buffer[2]<<16) + int(buffer[1]<<8) + buffer[0]]
		else:
			return [status, None]

	# Helper routine to write a specific value into a Value Block
	# 
	# Only for MIFARE Classic and only for blocks in "value block" mode, that
	# is: with access bits [C1 C2 C3] = [110] or [001]. The sector containing
	# the block must be authenticated before calling this function. 
	# 
	# @param[in]   blockAddr   The block (0x00-0xff) number
	# @param[in]   value	   New value of the Value Block
	# @return STATUS_OK on success, STATUS_??? otherwise
	def MIFARE_SetValue(	self,
							blockAddr,
							value
						):
		buffer = [None]*18

		# Translate the long into 4 bytes; repeated 2x in value block
		buffer[0] = buffer[ 8] = (value & 0xFF)
		buffer[1] = buffer[ 9] = (value & 0xFF00) >> 8
		buffer[2] = buffer[10] = (value & 0xFF0000) >> 16
		buffer[3] = buffer[11] = (value & 0xFF000000) >> 24
		# Inverse 4 bytes also found in value block
		buffer[4] = ~buffer[0]
		buffer[5] = ~buffer[1]
		buffer[6] = ~buffer[2]
		buffer[7] = ~buffer[3]
		# Address 2x with inverse address 2x
		buffer[12] = buffer[14] = blockAddr
		buffer[13] = buffer[15] = ~blockAddr

		# Write the whole data block
		return self.MIFARE_Write(blockAddr, buffer)

##########################################/
# Support functions
##########################################/

	# Wrapper for MIFARE protocol communication
	# Adds CRC_A, executes the Transceive command and checks that the response is MF_ACK or a timeout
	# 
	# @return STATUS_OK on success, STATUS_??? otherwise
	def PCD_MIFARE_Transceive(	self,
								sendData,				# Pointer to the data to transfer to the FIFO. Do NOT include the CRC_A
								sendLen=None,			# Number of bytes in sendData
								acceptTimeout=False		# True => A timeout is also success
							):
		cmdBuffer = [None]*18								# We need room for 16 bytes data and 2 bytes CRC_A

		sendLen = sendLen if sendLen else len(sendData)

		# Sanity check
		if not sendData or sendLen > 16:
			return self.STATUS_INVALID

		# Copy sendData[] to cmdBuffer[] and add CRC_A
		status, result = self.PCD_CalculateCRC(sendData, sendLen)

		if status != self.STATUS_OK: 
			return status

		cmdBuffer = sendData[:sendLen] + result
		sendLen += 2

		# Transceive the data, store the reply in cmdBuffer[]
		waitIRq = 0x30							# RxIRq and IdleIRq
		cmdBufferSize = len(cmdBuffer)
		validBits = 0
		status, cmdBuffer, cmdBufferSize, validBits = self.PCD_CommunicateWithPICC(self.PCD_Transceive, waitIRq, cmdBuffer, sendLen, cmdBufferSize, validBits)
		self.logger.debug("status: {}, cmdBuffer: {}, cmdBufferSize: {}, validBits: {}".format(status, cmdBuffer, cmdBufferSize, validBits))

		if acceptTimeout and status == self.STATUS_TIMEOUT:
			return self.STATUS_OK

		if status != self.STATUS_OK:
			return status

		# The PICC must reply with a 4 bit ACK
#		if cmdBufferSize != 1 or validBits != 4:
#			return self.STATUS_ERROR

		if cmdBuffer[0] != self.MF_ACK:
			return self.STATUS_MIFARE_NACK

		return self.STATUS_OK

	# Returns a status code name
	def GetStatusCodeName(	self,
							code	# One of the StatusCode enums
						):
		if code == self.STATUS_OK:					return "Success"
		elif code == self.STATUS_ERROR:				return "Error in communication"
		elif code == self.STATUS_COLLISION:			return "Collission detected"
		elif code == self.STATUS_TIMEOUT:			return "Timeout in communication"
		elif code == self.STATUS_NO_ROOM:			return "A buffer is not big enough"
		elif code == self.STATUS_INTERNAL_ERROR:	return "Internal error in the code. Should not happen"
		elif code == self.STATUS_INVALID:			return "Invalid argument"
		elif code == self.STATUS_CRC_WRONG:			return "The CRC_A does not match"
		elif code == self.STATUS_MIFARE_NACK:		return "A MIFARE PICC responded with NAK"
		else:
			return "Unknown error"

	# Translates the SAK (Select Acknowledge) to a PICC type
	# 
	# @return PICC_Type
	def PICC_GetType(	self,
						sak							# The SAK byte returned from PICC_Select()
					):
		if sak & 0x04:								# UID not complete
			return self.PICC_TYPE_NOT_COMPLETE

		if sak == 0x09:		return self.PICC_TYPE_MIFARE_MINI
		elif sak == 0x08:	return self.PICC_TYPE_MIFARE_1K
		elif sak == 0x18:	return self.PICC_TYPE_MIFARE_4K
		elif sak == 0x00:	return self.PICC_TYPE_MIFARE_UL
		elif sak == 0x10 or \
			 sak == 0x11:	return self.PICC_TYPE_MIFARE_PLUS
		elif sak == 0x01:	return self.PICC_TYPE_TNP3XXX

		if sak & 0x20:
			return self.PICC_TYPE_ISO_14443_4

		if sak & 0x40:
			return self.PICC_TYPE_ISO_18092

		return self.PICC_TYPE_UNKNOWN

	# Returns a __FlashStringHelper pointer to the PICC type name
	def PICC_GetTypeName(	self,
							piccType			# One of the PICC_Type enums
						):
		if piccType == self.PICC_TYPE_ISO_14443_4:		return "PICC compliant with ISO/IEC 14443-4"
		elif piccType == self.PICC_TYPE_ISO_18092:		return "PICC compliant with ISO/IEC 18092 (NFC)"
		elif piccType ==  self.PICC_TYPE_MIFARE_MINI:	return "MIFARE Mini, 320 bytes"
		elif piccType ==  self.PICC_TYPE_MIFARE_1K:		return "MIFARE 1KB"
		elif piccType ==  self.PICC_TYPE_MIFARE_4K:		return "MIFARE 4KB"
		elif piccType ==  self.PICC_TYPE_MIFARE_UL:		return "MIFARE Ultralight or Ultralight C"
		elif piccType == self.PICC_TYPE_MIFARE_PLUS:	return "MIFARE Plus"
		elif piccType ==  self.PICC_TYPE_TNP3XXX:		return "MIFARE TNP3XXX"
		elif piccType ==  self.PICC_TYPE_NOT_COMPLETE:	return "SAK indicates UID is not complete"
#		elif piccType ==  self.PICC_TYPE_UNKNOWN:
		else:
			return "Unknown type"

	# Dumps debug info about the selected PICC to Serial
	# On success the PICC is halted after dumping the data
	# For MIFARE Classic the factory default key of 0xFFFFFFFFFFFF is tried. 
	def PICC_DumpToSerial(self):
		# UID
		# Pointer to Uid struct returned from a successful PICC_Select()
		result = ""
		for ix in range(self.uid.size):
			if self.uid.uidByte[ix] != None:
				result += "0x{:02X} ".format(self.uid.uidByte[ix])
			else:
				self.logger.error("not correct uid")
				break
		print("Card UID: {}\n".format(result))

		# PICC type
		piccType = self.PICC_GetType(self.uid.sak)
		print("PICC type: ", self.PICC_GetTypeName(piccType), "\n")

		# Dump contents
		if piccType == self.PICC_TYPE_MIFARE_MINI or \
			piccType == self.PICC_TYPE_MIFARE_1K or \
			piccType == self.PICC_TYPE_MIFARE_4K:
			# All keys are set to FFFFFFFFFFFFh at chip delivery from the factory
			self.PICC_DumpMifareClassicToSerial(piccType, self.MIFARE_Key())

		elif piccType == self.PICC_TYPE_MIFARE_UL:
			self.PICC_DumpMifareUltralightToSerial()

		elif piccType == self.PICC_TYPE_ISO_14443_4 or \
			 piccType == self.PICC_TYPE_ISO_18092 or \
			 piccType == self.PICC_TYPE_MIFARE_PLUS or \
			 piccType == self.PICC_TYPE_TNP3XXX:
			print("Dumping memory contents not implemented for that PICC type")
				
		elif piccType == self.PICC_TYPE_UNKNOWN or \
			 piccType == self.PICC_TYPE_NOT_COMPLETE:
			 pass
		else:
			pass								# No memory dump here

		print()
		self.PICC_HaltA()						# Already done if it was a MIFARE Classic PICC

	# Dumps memory contents of a MIFARE Classic PICC
	# On success the PICC is halted after dumping the data
	def PICC_DumpMifareClassicToSerial(	self,
										piccType,	# One of the PICC_Type enums
										key			# Key A used for all sectors
										):
		no_of_sectors = 0
		if piccType == self.PICC_TYPE_MIFARE_MINI:
			# Has 5 sectors * 4 blocks/sector * 16 bytes/block = 320 bytes
			no_of_sectors = 5
		elif piccType == self.PICC_TYPE_MIFARE_1K:
			# Has 16 sectors * 4 blocks/sector * 16 bytes/block = 1024 bytes
			no_of_sectors = 16	
		elif piccType == self.PICC_TYPE_MIFARE_4K:
			# Has (32 sectors * 4 blocks/sector + 8 sectors * 16 blocks/sector) * 16 bytes/block = 4096 bytes
			no_of_sectors = 40
		else: # Should not happen. Ignore
			pass

		# Dump sectors, highest address first
		if no_of_sectors:
			print("Sector Block  00 01 02 03  04 05 06 07  08 09 10 11  12 13 14 15  AccessBits")
			for ix in range(no_of_sectors-1, -1, -1):
				self.PICC_DumpMifareClassicSectorToSerial(key, ix)

		self.PICC_HaltA()							# Halt the PICC before stopping the encrypted session
		self.PCD_StopCrypto1()

	# Dumps memory contents of a sector of a MIFARE Classic PICC
	# Uses PCD_Authenticate(), MIFARE_Read() and PCD_StopCrypto1
	# Always uses PICC_CMD_MF_AUTH_KEY_A because only Key A can always read the sector trailer access bits
	def PICC_DumpMifareClassicSectorToSerial(	self,
												key,			# Key A for the sector
												sector			# The sector to dump, 0..39
											):
		# The access bits are stored in a peculiar fashion
		# There are four groups:
		#		g[3]	Access bits for the sector trailer, block 3 (for sectors 0-31) or block 15 (for sectors 32-39)
		#		g[2]	Access bits for block 2 (for sectors 0-31) or blocks 10-14 (for sectors 32-39)
		#		g[1]	Access bits for block 1 (for sectors 0-31) or blocks 5-9 (for sectors 32-39)
		#		g[0]	Access bits for block 0 (for sectors 0-31) or blocks 0-4 (for sectors 32-39)
		# Each group has access bits [C1 C2 C3]. In this code C1 is MSB and C3 is LSB
		# The four CX bits are stored together in a nible cx and an inverted nible cx_
		g = [None]*4							# Access bits for each of the four groups

		# Determine position and size of sector
		# firstBlock - Address of lowest address to dump actually last block dumped)
		# no_of_blocks - Number of blocks in sector
		if sector < 32:							# Sectors 0..31 has 4 blocks each
			no_of_blocks = 4
			firstBlock = sector * no_of_blocks
		elif sector < 40:						# Sectors 32-39 has 16 blocks each
			no_of_blocks = 16
			firstBlock = 128 + (sector - 32) * no_of_blocks
		else:									# Illegal input, no MIFARE Classic PICC has more than 40 sectors
			return
			
		# Dump blocks, highest address first
		isSectorTrailer = True 			# Set to true while handling the "last" (ie highest address) in the sector
		for blockOffset in range(no_of_blocks-1, -1, -1):
			blockAddr = firstBlock + blockOffset
			# Sector number - only on first line
			if isSectorTrailer:
				result = "  {:02}   ".format(sector)
			else:
				result = "       "

			# Block number
			result += " {:03}   ".format(blockAddr)
			print(result, end="")

			# Establish encrypted communications before reading the first block
			if isSectorTrailer:
				self.logger.debug("firstBlock: {}, key: {}, self.uid: {}".format(firstBlock, key, self.uid))
				status = self.PCD_Authenticate(self.PICC_CMD_MF_AUTH_KEY_A, firstBlock, key, self.uid)[0]
				if status != self.STATUS_OK:
					print("PCD_Authenticate() failed: ", end="")
					print(self.GetStatusCodeName(status))
					return

			# Read block
			status, buffer = self.MIFARE_Read(blockAddr, 18)
			if status != self.STATUS_OK:
				print("MIFARE_Read() failed: ", end="")
				print(self.GetStatusCodeName(status))
				continue

			# Dump data
			result = ""
			for ix in range(16):
				if buffer[ix] != None:
					result += "{:02X} ".format(buffer[ix])
				else:
					self.logger.error("not correct Dump data")
					break
				if ix % 4 == 3:
					result += " "
			print(result, end="")



			# Parse sector trailer data
			if isSectorTrailer:
				# c1, c2, c3 - Nibbles
				# c1_, c2_, c3_ - Inverted nibbles
				c1  = buffer[7] >> 4
				c2  = buffer[8] & 0xF
				c3  = buffer[8] >> 4
				c1_ = buffer[6] & 0xF
				c2_ = buffer[6] >> 4
				c3_ = buffer[7] & 0xF
				# True if one of the inverted nibbles did not match
				invertedError = (c1 != ((~c1_) & 0xF)) or (c2 != ((~c2_) & 0xF)) or (c3 != ((~c3_) & 0xF))
				g[0] = ((c1 & 1) << 2) | ((c2 & 1) << 1) | ((c3 & 1) << 0)
				g[1] = ((c1 & 2) << 1) | ((c2 & 2) << 0) | ((c3 & 2) >> 1)
				g[2] = ((c1 & 4) << 0) | ((c2 & 4) >> 1) | ((c3 & 4) >> 2)
				g[3] = ((c1 & 8) >> 1) | ((c2 & 8) >> 2) | ((c3 & 8) >> 3)
				isSectorTrailer = False
			
			# Which access group is this block in?
			# group 0-3 - active group for access bits
			# firstInGroup - True for the first block dumped in the group
			if no_of_blocks == 4:
				group = blockOffset
				firstInGroup = True
			else:
				group = int(blockOffset / 5)
				firstInGroup = (group == 3) or int(group != (blockOffset + 1) / 5)
			
			if firstInGroup:
				# Print access bits
				print(" [ {} {} {} ] ".format( ((g[group] >> 2) & 1), ((g[group] >> 1) & 1), ((g[group] >> 0) & 1) ))

				if invertedError:
					print(" Inverted access bits did not match! ")

			if group != 3 and (g[group] == 1 or g[group] == 6):		# Not a sector trailer, a value block
				value = int(buffer[3]<<24) | int(buffer[2]<<16) | int(buffer[1]<<8) | buffer[0]
				print(" Value=0x{:02X} Adr=0x{:02X}".format(value, buffer[12]))

		return

	# Dumps memory contents of a MIFARE Ultralight PICC
	def PICC_DumpMifareUltralightToSerial(self):
		print("Page  0  1  2  3")
		# Try the mpages of the original Ultralight. Ultralight C has more pages
		for page in range(0, 16, 4):			# Read returns data for 4 pages at a time
			# Read pages
			status, buffer = self.MIFARE_Read(page, 18)
			if status != self.STATUS_OK:
				print("MIFARE_Read() failed: ", end="")
				print(self.GetStatusCodeName(status))

			# Dump data
			result = ""
			for offset in range(4):
				ix = page + offset
				print(" {:2}".format(ix), end="")
				print("  ", end="")
				for iy in range(4):
					ix = 4 * offset + iy
					if buffer[ix] != None:
						result += "0x{:02X} ".format(buffer[ix])
					else:
						self.logger.error("not correct Dump data")
						break
				print(result)

	# Calculates the bit pattern needed for the specified access bits. In the [C1 C2 C3] tupples C1 is MSB (=4) and C3 is LSB (=1)
	def MIFARE_SetAccessBits(	self,
								g0,					# Access bits [C1 C2 C3] for block 0 (for sectors 0-31) or blocks 0-4 (for sectors 32-39)
								g1,					# Access bits C1 C2 C3] for block 1 (for sectors 0-31) or blocks 5-9 (for sectors 32-39)
								g2,					# Access bits C1 C2 C3] for block 2 (for sectors 0-31) or blocks 10-14 (for sectors 32-39)
								g3					# Access bits C1 C2 C3] for the sector trailer, block 3 (for sectors 0-31) or block 15 (for sectors 32-39)
							):
		c1 = ((g3 & 4) << 1) | ((g2 & 4) << 0) | ((g1 & 4) >> 1) | ((g0 & 4) >> 2)
		c2 = ((g3 & 2) << 2) | ((g2 & 2) << 1) | ((g1 & 2) << 0) | ((g0 & 2) >> 1)
		c3 = ((g3 & 1) << 3) | ((g2 & 1) << 2) | ((g1 & 1) << 1) | ((g0 & 1) << 0)

		# accessBitBuffer - byte 6, 7 and 8 in the sector trailer. Bytes [0..2] will be set
		accessBitBuffer[0] = ((~c2) & 0xF) << 4 | ((~c1) & 0xF)
		accessBitBuffer[1] =			c1 << 4 | ((~c3) & 0xF)
		accessBitBuffer[2] =			c3 << 4 | c2

		return accessBitBuffer

	# Performs the "magic sequence" needed to get Chinese UID changeable
	# Mifare cards to allow writing to sector 0, where the card UID is stored
	#
	# Note that you do not need to have selected the card through REQA or WUPA,
	# this sequence works immediately when the card is in the reader vicinity
	# This means you can use this method even on "bricked" cards that your reader does
	# not recognise anymore (see MFRC522::MIFARE_UnbrickUidSector)
	# 
	# Of course with non-bricked devices, you're free to select them before calling this function
	def MIFARE_OpenUidBackdoor(self):
		# Magic sequence:
		# > 50 00 57 CD (HALT + CRC)
		# > 40 (7 bits only)
		# < A (4 bits only)
		# > 43
		# < A (4 bits only)
		# Then you can write to sector 0 without authenticating

		self.PICC_HaltA()						# 50 00 57 CD

		validBits = 7							# Our command is only 7 bits. After receiving card response,
												# this will contain amount of valid response bits
		# response = [None]*32					# Card's response is written here
		status, response, backLen = self.PCD_TransceiveData([0x40], 1, -1, validBits, 0, False)[:3]	# 40
		self.logger.debug("status: {}, response: {}, backLen: {}".format(status, response, backLen))
		if status != self.STATUS_OK:
			self.logger.error("Card did not respond to 0x40 after HALT command. Are you sure it is a UID changeable one?")
			self.logger.error("Error name: {}".format(self.GetStatusCodeName(status)))

			return False

		if backLen != 1 or response[0] != 0x0A:
			self.logger.error("Got bad response on backdoor 0x40 command: 0x{:X} ({} valid bits)".format(response[0], validBits))
			return False

		validBits = 8
		status, response, backLen = self.PCD_TransceiveData([0x43], 1, -1, validBits, 0, False)[:3]	# 43
		self.logger.debug("status: {}, response: {}, backLen: {}".format(status, response, backLen))
		if status != self.STATUS_OK:
			self.logger.error("Error in communication at command 0x43, after successfully executing 0x40")
			self.logger.error("Error name: {}".format(self.GetStatusCodeName(status)))

			return False

		if backLen != 1 or response[0] != 0x0A:
			self.logger.error("Got bad response on backdoor 0x43 command: {:X} ({} valid bits)".format(response[0], validBits))
			return False

		# You can now write to sector 0 without authenticating!
		return True

	# Reads entire block 0, including all manufacturer data, and overwrites
	# that block with the new UID, a freshly calculated BCC, and the original
	# manufacturer data
	#
	# It assumes a default KEY A of 0xFFFFFFFFFFFF
	# Make sure to have selected the card before this function is called
	def MIFARE_SetUid(	self,
						newUid,
						uidSize
					):
		# UID + BCC byte can not be larger than 16 together
		if not newUid or not uidSize or uidSize > 15:
			self.logger.error("New UID buffer empty, size 0, or size > 15 given")
			return False

		# Authenticate for reading
		status = self.PCD_Authenticate(self.PICC_CMD_MF_AUTH_KEY_A, 1, self.MIFARE_Key(), self.uid)[0]
		if status != self.STATUS_OK:
			if status == self.STATUS_TIMEOUT:
				# We get a read timeout if no card is selected yet, so let's select one
				
				# Wake the card up again if sleeping
#				byte atqa_answer[2]
#				byte atqa_size = 2
#				PICC_WakeupA(atqa_answer, &atqa_size)

				if not self.PICC_IsNewCardPresent() or not self.PICC_ReadCardSerial():
					print("No card was previously selected, and none are available. Failed to set UID.")
					return False
				
				status = self.PCD_Authenticate(self.PICC_CMD_MF_AUTH_KEY_A, 1, self.MIFARE_Key(), self.uid)[0]
				if status != self.STATUS_OK:
					# We tried, time to give up
					self.logger.error("Failed to authenticate to card for reading, could not set UID: ", end="")
					self.logger.error(self.GetStatusCodeName(status))

					return False

			else:
				self.logger.error("PCD_Authenticate() failed: ", end="")
				self.logger.error(self.GetStatusCodeName(status))

				return False

		# Read block 0
		status, block0_buffer = self.MIFARE_Read(0, 18)
		self.logger.debug("status: {}, block0_buffer: {}".format(status, block0_buffer))
		if status != self.STATUS_OK:
			self.logger.error("MIFARE_Read() failed: ", end="")
			self.logger.error(self.GetStatusCodeName(status))
			self.logger.error("Are you sure your KEY A for sector 0 is 0xFFFFFFFFFFFF?")

			return False

		# Write new UID to the data we just read, and calculate BCC byte
		bcc = 0
		for ix in range(uidSize):
			block0_buffer[ix] = newUid[ix]
			bcc ^= newUid[ix]

		# Write BCC byte to buffer
		block0_buffer[uidSize] = bcc

		# Stop encrypted traffic so we can send raw bytes
		self.PCD_StopCrypto1()

		# Activate UID backdoor
		if not self.MIFARE_OpenUidBackdoor():
			self.logger.error("Activating the UID backdoor failed.")

			return False

		# Write modified block 0 back to card
		status = self.MIFARE_Write(0, block0_buffer, 16)
		if status != self.STATUS_OK:
			self.logger.error("MIFARE_Write() failed: ", end="")
			self.logger.error(self.GetStatusCodeName(status))

			return False

		# Wake the card up again
		atqa_size = 2
		status, atqa_answer = self.PICC_WakeupA(atqa_size)

		return True

	# Resets entire sector 0 to zeroes, so the card can be read again by readers
	def MIFARE_UnbrickUidSector(self):
		self.MIFARE_OpenUidBackdoor()

		block0_buffer = [0x01, 0x02, 0x03, 0x04, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

		# Write modified block 0 back to card
		status = self.MIFARE_Write(0, block0_buffer)	# , 16 - можно не указывать, по дефолту для записи используется весь буфер
		if status != self.STATUS_OK:
			self.logger.error("MIFARE_Write() failed: ", end="")
			self.logger.error(self.GetStatusCodeName(status))

			return False

################################################################################
#			Convenience functions - does not add extra functionality		   #
################################################################################

	# Returns true if a PICC responds to PICC_CMD_REQA
	# Only "new" cards in state IDLE are invited. Sleeping cards in state HALT are ignored
	# 
	# @return bool
	def PICC_IsNewCardPresent(self):
		bufferSize = 2
		status, bufferATQA = self.PICC_RequestA(bufferSize)
		return status == self.STATUS_OK or status == self.STATUS_COLLISION

	# Simple wrapper around PICC_Select
	# Returns true if a UID could be read
	# Remember to call PICC_IsNewCardPresent(), PICC_RequestA() or PICC_WakeupA() first
	# The read UID is available in the class variable uid
	# 
	# @return bool
	def PICC_ReadCardSerial(self):
		return self.PICC_Select() == self.STATUS_OK

	def wait(self):
		try:
			while not self.PICC_IsNewCardPresent():
				print(".", end="")
				sys.stdout.flush()
				sleep(1)
			if not self.logLevel == logging.DEBUG: print()
		except KeyboardInterrupt:
			print()
			self.logger.info("Interrupted by user")
			return False

		return self.PICC_ReadCardSerial()

	def dump(self):
		if self.wait():
			self.PICC_DumpToSerial()

	# 0x9C, 0x3A, 0xD8, 0xAE - купчино
	# 0x49, 0x4C, 0x3E, 0x99 - солидарности
	def write(self, newUid=[0x49, 0x4C, 0x3E, 0x99]):
		if self.wait():
			self.MIFARE_SetUid(newUid, len(newUid))

	def test(self, sector=8):
		self.wait()
		s = [None]*4
		if self.PCD_Authenticate(self.PICC_CMD_MF_AUTH_KEY_A, 8, self.MIFARE_Key(), self.uid)[0] == 1:
			for ix in range(4):
				s[ix] = self.MIFARE_Read(8+ix,18)[1][:16]
		for ix in range(4):
			for iy in range(16):
				print(chr(s[ix][iy]), end="")
			if ix != 3:
				print("+", end="")
			else:
				print()

	def read(self):
		print("Waiting for card:")
		if not self.wait():
			self.logger.error("map reading shit")
			return

		print("================================================")
		print("Card UID: 0x", end="")
		for ix in range(self.uid.size):
			print("{:02X}".format(self.uid.uidByte[ix]), end="")
		print()

		print("================================================")
		piccType = self.PICC_GetType(self.uid.sak)
		print("Card type: {}".format(self.PICC_GetTypeName(piccType)))
		print("================================================")

		if piccType != self.PICC_TYPE_MIFARE_UL:
			print("Not a valid card: {}".format(piccType))
			print("================================================")
			self.PICC_HaltA()
			return

		for ix in [4, 6, 8]:			# начинаем читать страницы с данными
			status, buffer = self.MIFARE_Read(ix, 18)
			if status != self.STATUS_OK:
				self.logger.error("Read error: {}".format(self.GetStatusCodeName(status)))
			elif ix == 4:
				bCounter = 0		# 32-битный счетчик для номера
				for bCount in range(4):
					pass
