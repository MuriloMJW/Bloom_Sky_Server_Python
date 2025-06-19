import struct
from io import BytesIO

# Tipos de dados suportados para leitura\BUFFER_U8 = 1  # Leitura de um único byte (unsigned 8-bit)
BUFFER_U8 = 1  # Leitura de 1 byte
BUFFER_U16 = 2  # Leitura de 2 bytes
BUFFER_STRING = 3  # Leitura de strings terminadas por byte nulo (0x00)


class MyBuffer:
    """
    Classe para leitura sequencial de dados de um buffer de bytes.
    """

    def __init__(self, buffer):
        """
        Inicializa o buffer de leitura.

        :param buffer: Sequência de bytes a ser lida
        """
        self.buffer = buffer  # Dados brutos do buffer
        self.pos = 0  # Posição atual de leitura (em bytes)
        self.length = len(buffer)  # Comprimento total do buffer
        self.buf = BytesIO(buffer)  # Objeto BytesIO para operações de leitura
        
    def read_u8(self):
        data = self.buf.read(BUFFER_U8)
        self.pos = self.buf.tell()  # Atualiza posição de leitura
        return data[0]
    
    def read_u16(self):
        # Lê 2 bytes e converte para inteiro
        data = self.buf.read(BUFFER_U16)
        self.pos = self.buf.tell()  # Atualiza posição de leitura
        (aux, ) = struct.unpack('H', data)  # H = short (2 bytes)
        return aux
        
    def read_string(self):
        # Encontra o próximo byte nulo (0x00) a partir da posição atual
        pos_null = self.buffer.index(0, self.buf.tell())
        # Calcula o tamanho da string em bytes (excluindo o byte nulo)
        size = pos_null - self.buf.tell()
        # Lê e decodifica a sequência de bytes como ASCII
        text = self.buf.read(size).decode('ascii')
        # Consome o byte nulo final e atualiza a posição
        self.buf.read(1)
        self.pos = self.buf.tell()
        return str(text)
        
        
    def write_u8(self, data):
        _data = struct.pack("B", data)
        self.pos += BUFFER_U8
        self.buffer += _data
        
    def write_u16(self, data):
        _data = struct.pack("H", data)
        self.pos += BUFFER_U16
        self.buffer += _data
        
    def write_string(self, data):
        text_encoded = data.encode('ascii')
        text_size = len(text_encoded)
        #_data = struct.pack(f'{text_size}s', text_encoded) com 0 no final
        _data = struct.pack(f'{text_size}s', text_encoded)

        self.pos += text_size
        self.buffer += _data
        
    def buffer_read(self, data_type):
        """
        Lê dados do buffer com base no tipo especificado.

        :param data_type: Tipo de dado a ser lido (BUFFER_U8 ou BUFFER_STRING)
        :return: Valor lido (int para BUFFER_U8 ou str para BUFFER_STRING)
        """
        if data_type == BUFFER_U8:
            # Lê um único byte e converte para inteiro
            #self.buf.seek(self.pos)
            data = self.buf.read(BUFFER_U8)
            self.pos = self.buf.tell()  # Atualiza posição de leitura
            return data[0]

        if data_type == BUFFER_U16:
            # Lê 2 bytes e converte para inteiro
            data = self.buf.read(BUFFER_U16)
            self.pos = self.buf.tell()  # Atualiza posição de leitura
            (aux, ) = struct.unpack('H', data)  # H = short (2 bytes)
            return aux

        if data_type == BUFFER_STRING:
            # Encontra o próximo byte nulo (0x00) a partir da posição atual
            pos_null = self.buffer.index(0, self.buf.tell())
            # Calcula o tamanho da string em bytes (excluindo o byte nulo)
            size = pos_null - self.buf.tell()
            # Lê e decodifica a sequência de bytes como ASCII
            text = self.buf.read(size).decode('ascii')
            # Consome o byte nulo final e atualiza a posição
            self.buf.read(1)
            self.pos = self.buf.tell()
            return str(text)

    def buffer_write(self, data_type, data):
        """
        Escreve dados do buffer com base no tipo especificado.

        :param data_type: Tipo de dado a ser lido (BUFFER_U8 ou BUFFER_STRING)
        :return: Valor lido (int para BUFFER_U8 ou str para BUFFER_STRING)
        """
        if data_type == BUFFER_U8:
            _data = struct.pack("B", data)
            self.pos += BUFFER_U8
            self.buffer += _data

        if data_type == BUFFER_U16:
            _data = struct.pack("H", data)
            self.pos += BUFFER_U16
            self.buffer += _data

        if data_type == BUFFER_STRING:

            text_encoded = data.encode('ascii')
            text_size = len(text_encoded)
            #_data = struct.pack(f'{text_size}s', text_encoded) com 0 no final
            _data = struct.pack(f'{text_size}s', text_encoded)

            self.pos += text_size
            self.buffer += _data

    def buffer_reset(self):
        self.pos = 0






#texto = "Hello"
#texto_encoded = texto.encode("ascii")
#packed = struct.pack(f"B{len(texto_encoded)}sx", num, texto_encoded)

# B   = tamanho de 1 byte
# 10s = Quantidade de bytes da String
# x   = Byte nulo

#print("Enviado")
#print(packed)
#print(type(packed))

#print("Traduzido")
#myBuffer = MyBuffer(packed)
#print(myBuffer.buffer_read(BUFFER_U8))
#print(myBuffer.buffer_read(BUFFER_STRING))
""""
testeBuffer = bytearray(b'\x05HELLO\x00WORLD\x00')

myBuffer = MyBuffer(testeBuffer)

print(myBuffer.buffer_read(BUFFER_U8))
print(myBuffer.buffer_read(BUFFER_STRING))
print(myBuffer.buffer_read(BUFFER_STRING))





buffer = bytearray(b'\x05HELLO\x00WORLD\x00')

buf = BytesIO(buffer)

msgid = buf.read(1)

pos_null = buffer.index(0, buf.tell())
tamanho = pos_null - buf.tell() #Tamanho da String

print(tamanho)

texto1 = buf.read(tamanho).decode('ascii') #Le o tamanho da string

print(texto1)
buf.read(1)

pos_null = buffer.index(0, buf.tell())
tamanho = pos_null - buf.tell() #Tamanho da String


texto2 = buf.read(tamanho).decode('ascii') #Le o tamanho da string

print(texto2)
#buffer.index(0, 1), procura o byte 0, a partir de onde o ponteiro está (buf.tell())





bytearray(b'\x05HELLO\x00WORLD\x00')

msgid = 5
chat = "Hello World"


buffer = bytearray([msgid])

buffer.extend(chat.encode('ascii'))

buffer.append(0)
"""

#print(buffer)

# ┌────────────────────────────────────────────────────────────────────────────┐
# │                          Códigos do módulo struct                          │
# └────────────────────────────────────────────────────────────────────────────┘
#
#   Código  | Descrição            | Tamanho | Intervalo de valores possíveis
#  ─────────┼──────────────────────┼─────────┼──────────────────────────────────
#   b       | signed char          | 1 byte  | -128 … 127
#   B       | unsigned char        | 1 byte  | 0 … 255
#   ?       | boolean (_Bool)      | 1 byte  | False (0) ou True (1)
#   h       | signed short         | 2 bytes | -32 768 … 32 767
#   H       | unsigned short       | 2 bytes | 0 … 65 535
#   i       | signed int           | 4 bytes | -2 147 483 648 … 2 147 483 647
#   I       | unsigned int         | 4 bytes | 0 … 4 294 967 295
#   l       | signed long          | 4 bytes | -2 147 483 648 … 2 147 483 647
#   L       | unsigned long        | 4 bytes | 0 … 4 294 967 295
#   q       | signed long long     | 8 bytes | -9 223 372 036 854 775 808 … 9 223 372 036 854 775 807
#   Q       | unsigned long long   | 8 bytes | 0 … 18 446 744 073 709 551 615
#   f       | float (IEEE 754)     | 4 bytes | aprox. -3.4 × 10³⁸ … 3.4 × 10³⁸
#   d       | double (IEEE 754)    | 8 bytes | aprox. -1.8 × 10³⁰⁸ … 1.8 × 10³⁰⁸
#
# ┌────────────────────────────────────────────────────────────────────────────┐
# │                              Endianess                                     │
# └────────────────────────────────────────────────────────────────────────────┘
#
#   Prefixo | Ordem de bytes           | Descrição
#  ─────────┼──────────────────────────┼────────────────────────────────────────────
#   '<'     | little-endian            | menor byte (LSB) vem primeiro na sequência
#   '>'     | big-endian               | maior byte (MSB) vem primeiro na sequência
#   '!'     | network (= big-endian)   | mesma coisa que '>' (padrão em protocolos de rede)
#
# Exemplo de uso:
#   import struct
#   # little-endian: int 1000 → bytes '\xE8\x03\x00\x00'
#   b_le = struct.pack('<I', 1000)
#   # big-endian:    int 1000 → bytes '\x00\x00\x03\xE8'
#   b_be = struct.pack('>I', 1000)
