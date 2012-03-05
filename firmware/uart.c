#include <avr/io.h>
#include <avr/interrupt.h>

#include "uart.h"

volatile unsigned char uart_rxpos, uart_rxfin;
char uart_rxbuf[20];

SIGNAL(SIG_UART_RECV)
{
    uart_rxbuf[uart_rxpos] = UDR;
    if (!uart_rxfin) {
        if (uart_rxbuf[uart_rxpos] == 13) {     // CR
            uart_rxbuf[uart_rxpos + 1] = 0;
            uart_rxpos += 2;
            uart_rxfin = 1;
        } else {
            uart_rxpos++;
            if (uart_rxpos == 20)
                uart_rxpos = 0;
        }
    }
}

void uart_init(void)
{
    uart_rxpos = 0;
    uart_rxfin = 0;
    UBRRL = 25;                 //19200 @ 8MHz
    UCSRB = _BV(TXEN) | _BV(RXEN) | _BV(RXCIE);
}

void uart_putstr(char *data)
{
    while (*data) {
        loop_until_bit_is_set(UCSRA, UDRE);
        UDR = *data;
        data++;
    }
}

char *uart_received()
{
    if (uart_rxfin)
        return uart_rxbuf;
    else
        return 0;
}

void uart_empty()
{
    uart_rxfin = 0;
    uart_rxpos = 0;
}
