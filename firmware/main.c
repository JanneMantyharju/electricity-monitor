#define F_CPU 8000000UL

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/eeprom.h>
#include <string.h>
#include <util/delay.h>

#include "uart.h"

#define MAXCOMMAND 20           //maximum command length
#define BOOTED  50

unsigned int counter = 0;
unsigned int interval;

void print5(unsigned int x, char *buf);

void uart_handle(char *uart_rxbuf)
{
    unsigned int i;
    char buf[20];

    if (!strncmp("VALI", uart_rxbuf, 4)) {
        print5(interval, buf);
        uart_putstr(buf);
        uart_putstr("\r");
    } else if (!strncmp("LUKU", uart_rxbuf, 4)) {
        print5(counter, buf);
        counter = 0;
        uart_putstr(buf);
        uart_putstr("\r");
    } else if (!strncmp("SAVE", uart_rxbuf, 4)) {
        for (i = 0; i < 10; i++) {
            eeprom_update_byte((uint8_t *) i, uart_rxbuf[i + 4]);
            eeprom_busy_wait();
        }
        eeprom_update_byte((uint8_t *) BOOTED, 0);
        uart_putstr("OK\r");
    } else if (!strncmp("LOAD", uart_rxbuf, 4)) {
        if (eeprom_read_byte((uint8_t *) BOOTED)) {
            uart_putstr("BOOTED\r");
        } else {
            for (i = 0; i < 10; i++) {
                loop_until_bit_is_set(UCSRA, UDRE);
                UDR = eeprom_read_byte((uint8_t *) i);
            }
        }
    } else
        uart_putstr("ERR\r");

    uart_empty();
}

void print5(unsigned int x, char *buf)
{
    unsigned int y;
    unsigned char lead = 0, pos = 0;

    if (x < 65535) {
        y = x / 10000;
        if (y) {
            buf[pos] = y + 0x30;
            pos++;
            lead = 1;
        }
        x -= (y * 10000);

        y = x / 1000;
        if (y || lead) {
            buf[pos] = y + 0x30;
            pos++;
            lead = 1;
        }
        x -= (y * 1000);

        y = x / 100;
        if (y || lead) {
            buf[pos] = y + 0x30;
            pos++;
            lead = 1;
        }
        x -= (y * 100);

        y = x / 10;
        if (y || lead) {
            buf[pos] = y + 0x30;
            pos++;
        }
        x -= (y * 10);

        buf[pos] = x + 0x30;
        pos++;
        buf[pos] = 0;
    }
}

int main(void)
{
    char *buffer;
    unsigned char lock = 0;

    uart_init();
    uart_putstr("INIT\r");
    sei();
    DDRD = 0xFF;
    DDRB = 0xFF;

    PORTB |= _BV(PB3);
    eeprom_update_byte((uint8_t *) BOOTED, 1);

    TCCR1B = _BV(CS12) | _BV(CS10);

    while (1) {
        buffer = uart_received();
        if (buffer)
            uart_handle(buffer);
        if (!bit_is_set(PINC, PC2)) {
            if (!lock) {
                PORTB |= _BV(PB3);
                counter++;
                interval = TCNT1L;
                interval += TCNT1H * 0xff;
                TCNT1H = 0;
                TCNT1L = 0;
                lock = 1;
                _delay_ms(100);
            }
        } else {
            PORTB &= ~_BV(PB3);
            lock = 0;
            _delay_ms(20);
        }
    }

    return 0;
}
