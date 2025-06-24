import struct
from io import BytesIO

# Tipos de dados suportados para leitura\BUFFER_U8 = 1  # Leitura de um único byte (unsigned 8-bit)
BUFFER_U8 = 1   # Leitura de 1 byte
BUFFER_U16 = 2  # Leitura de 2 bytes
BUFFER_U32 = 4  # Leitura de 4 bytes
BUFFER_U64 = 8  # Leitura de 8 bytes
BUFFER_STRING = 9  # Leitura de strings terminadas por byte nulo (0x00)

# Ideia de herdar da byte array e mudar tudo para self

class MyBuffer:
    """
    Classe para leitura sequencial de dados de um buffer de bytes.
    """

    def __init__(self, data: bytes=b''):
        """
        Inicializa o buffer de leitura.

        :param buffer: Sequência de bytes a ser lida
        """
        self.data_array = bytearray(data)  # Se eu quiser já instanciar com parametro
        self.pos = 0  # Posição atual de leitura (em bytes)
        
    def read_u8(self):
        data = self.data_array[self.pos]
        self.pos += 1  # Atualiza posição de leitura
        return data
    
    def read_u16(self):
        # Lê 2 bytes e converte para inteiro
        (data,) = struct.unpack_from('H', self.data_array, self.pos)
        self.pos += BUFFER_U16  # Atualiza posição de leitura
        return data
    
    def read_u32(self):
        # Lê 4 bytes e converte para inteiro
        (data,) = struct.unpack_from('I', self.data_array, self.pos)
        self.pos += BUFFER_U32  # Atualiza posição de leitura
        return data
    
    def read_u64(self):
        # Lê 8 bytes e converte para inteiro
        (data,) = struct.unpack_from('Q', self.data_array, self.pos)
        self.pos += BUFFER_U64  # Atualiza posição de leitura
        return data
        
    def read_string(self):
        
        start = self.pos
        
        # Procura a posição do byte nulo, a partir do da posição de leitura atual
        # end é posição do buffer do byte nulo, ou seja, onde termina a string
        end = self.data_array.find(0, self.pos)
        
        # Tamanho da string é a posição do caractere final menos a posição do inicial
        #string_size =  end - start
        
        # Recebe uma tupla de 1 elemento do tipo bytes, esse elemento possui tamanho string_size
        #(text_encoded,) = struct.unpack_from(f'{string_size}s', self.data_array, start)
        # Converte em string ascii
        #text_decoded = text_encoded.decode('ascii')
        
        # Alternativa com slice: 
        text_encoded = self.data_array[start:end]
        text_decoded = text_encoded.decode('ascii')
        
        self.pos = end + 1  # Atualiza posição de leitura (pula o byte nulo)
        
        return text_decoded
        
    def write_u8(self, data):
        self.data_array += struct.pack('B', data)
        self.pos += BUFFER_U8
        
    def write_u16(self, data):
        data_bytes = struct.pack("H", data)
        self.data_array += data_bytes
        self.pos += BUFFER_U16
    
    def write_u32(self, data):
        data_bytes = struct.pack("I", data)
        self.data_array += data_bytes
        self.pos += BUFFER_U32
        
    def write_u64(self, data):
        data_bytes = struct.pack("Q", data)
        self.data_array += data_bytes
        self.pos += BUFFER_U64
        
    def write_string(self, data):
        text_encoded = data.encode('ascii')
        string_size = len(text_encoded)
        #_data = struct.pack(f'{text_size}sx', text_encoded) com 0 no final
        self.data_array += struct.pack(f'{string_size}sx', text_encoded)

        self.pos += string_size
        
    def seek_start(self):
        self.pos = 0
        
    def seek(self, pos: int):
        self.pos = pos
        
    def clear(self):
        self.data_array = b''
        self.pos = 0
    
    def get_data_array(self):
        return self.data_array


'''
buffer = MyBuffer()
buffer.write_u16(256)
#buffer.write_u8(0)
buffer.seek(0)
print(buffer.read_u16())
'''




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
